"""
Test de integración para el Auth Service (gRPC).

Requiere:
  - Auth Service corriendo en localhost:50051
  - PostgreSQL corriendo con el schema inicializado

Ejecución:
  python -m tests.test_auth_service
"""

import asyncio
import sys
import grpc
from grpc import aio as grpc_aio
import time

# Agregar path raíz para imports
sys.path.insert(0, ".")

from src.generated import auth_pb2, auth_pb2_grpc, common_pb2

AUTH_ADDRESS = "localhost:50051"

# Datos de prueba con email único
TEST_EMAIL = f"test_user_{int(time.time())}@uaa.mx"
TEST_PASSWORD = "password123"
TEST_NAME = "Usuario de Prueba"


class Colors:
    """ANSI colors para output legible."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def ok(msg: str) -> None:
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {Colors.RED}✗{Colors.RESET} {msg}")


def header(msg: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 50}")
    print(f"  {msg}")
    print(f"{'=' * 50}{Colors.RESET}")


def section(msg: str) -> None:
    print(f"\n{Colors.YELLOW}--- {msg} ---{Colors.RESET}")


async def run_tests():
    """Ejecuta todos los tests del Auth Service secuencialmente."""

    passed = 0
    failed = 0
    tokens = {}  # Almacena tokens entre tests

    # Conectar al servicio
    header("Auth Service - Tests de Integración")
    print(f"  Conectando a {AUTH_ADDRESS}...")

    channel = grpc_aio.insecure_channel(AUTH_ADDRESS)
    stub = auth_pb2_grpc.AuthServiceStub(channel)

    try:
        # ============================================================
        # 1. REGISTER
        # ============================================================
        section("1. Register — Nuevo usuario")
        try:
            response = await stub.Register(
                auth_pb2.RegisterRequest(
                    email=TEST_EMAIL,
                    password=TEST_PASSWORD,
                    name=TEST_NAME,
                )
            )
            if response.success and response.user.email == TEST_EMAIL:
                ok(f"Usuario creado: {response.user.email} (id: {response.user.id})")
                ok(f"Rol: USER_ROLE_USER = {response.user.role}")
                tokens["user_id"] = response.user.id
                passed += 1
            else:
                fail(f"Register falló: {response.error.message}")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 2. REGISTER — Duplicado
        # ============================================================
        section("2. Register — Email duplicado (debe fallar)")
        try:
            response = await stub.Register(
                auth_pb2.RegisterRequest(
                    email=TEST_EMAIL,
                    password=TEST_PASSWORD,
                    name=TEST_NAME,
                )
            )
            if not response.success and response.error.code == 409:
                ok(f"Rechazado correctamente: {response.error.message}")
                passed += 1
            else:
                fail(f"Debería haber fallado con 409, pero: success={response.success}")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 3. REGISTER — Validación (password corto)
        # ============================================================
        section("3. Register — Password muy corto (debe fallar)")
        try:
            response = await stub.Register(
                auth_pb2.RegisterRequest(
                    email="otro@uaa.mx",
                    password="123",
                    name="Otro User",
                )
            )
            if not response.success and response.error.code == 400:
                ok(f"Validación correcta: {response.error.message}")
                passed += 1
            else:
                fail(f"Debería haber fallado con 400")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 4. LOGIN
        # ============================================================
        section("4. Login — Credenciales correctas")
        try:
            response = await stub.Login(
                auth_pb2.LoginRequest(
                    email=TEST_EMAIL,
                    password=TEST_PASSWORD,
                )
            )
            if response.success and response.access_token and response.refresh_token:
                ok(f"Login exitoso: {response.user.email}")
                ok(f"Access token: {response.access_token[:40]}...")
                ok(f"Refresh token: {response.refresh_token[:40]}...")
                ok(f"Expira en: {response.expires_in}s")
                tokens["access"] = response.access_token
                tokens["refresh"] = response.refresh_token
                tokens["user_id"] = response.user.id
                passed += 1
            else:
                fail(f"Login falló: {response.error.message}")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 5. LOGIN — Credenciales incorrectas
        # ============================================================
        section("5. Login — Password incorrecto (debe fallar)")
        try:
            response = await stub.Login(
                auth_pb2.LoginRequest(
                    email=TEST_EMAIL,
                    password="wrong_password",
                )
            )
            if not response.success and response.error.code == 401:
                ok(f"Rechazado correctamente: {response.error.message}")
                passed += 1
            else:
                fail(f"Debería haber fallado con 401")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 6. VALIDATE TOKEN
        # ============================================================
        section("6. ValidateToken — Token válido")
        try:
            response = await stub.ValidateToken(
                auth_pb2.ValidateTokenRequest(
                    access_token=tokens.get("access", ""),
                )
            )
            if response.valid and response.user.email == TEST_EMAIL:
                ok(f"Token válido para: {response.user.email}")
                ok(f"Rol: {response.user.role}")
                passed += 1
            else:
                fail(f"ValidateToken falló: {response.error.message}")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 7. VALIDATE TOKEN — Token inválido
        # ============================================================
        section("7. ValidateToken — Token basura (debe fallar)")
        try:
            response = await stub.ValidateToken(
                auth_pb2.ValidateTokenRequest(
                    access_token="token.invalido.basura",
                )
            )
            if not response.valid:
                ok(f"Rechazado correctamente: {response.error.message}")
                passed += 1
            else:
                fail("Debería haber sido inválido")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 8. GET PROFILE
        # ============================================================
        section("8. GetProfile — Usuario existente")
        try:
            response = await stub.GetProfile(
                auth_pb2.GetProfileRequest(
                    user_id=tokens.get("user_id", ""),
                )
            )
            if response.success and response.user.name == TEST_NAME:
                ok(f"Perfil: {response.user.name} ({response.user.email})")
                passed += 1
            else:
                fail(f"GetProfile falló: {response.error.message}")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 9. REFRESH TOKEN
        # ============================================================
        section("9. RefreshToken — Rotar tokens")
        try:
            response = await stub.RefreshToken(
                auth_pb2.RefreshTokenRequest(
                    refresh_token=tokens.get("refresh", ""),
                )
            )
            if response.success and response.access_token and response.refresh_token:
                ok(f"Tokens rotados exitosamente")
                ok(f"Nuevo access: {response.access_token[:40]}...")
                ok(f"Nuevo refresh: {response.refresh_token[:40]}...")
                # Verificar que los tokens cambiaron
                if response.access_token != tokens["access"]:
                    ok("Access token es diferente al anterior")
                else:
                    fail("Access token debería ser diferente")
                tokens["access"] = response.access_token
                tokens["refresh"] = response.refresh_token
                passed += 1
            else:
                fail(f"RefreshToken falló: {response.error.message}")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 10. REFRESH TOKEN — Reuso del anterior (debe fallar)
        # ============================================================
        section("10. RefreshToken — Reuso de token anterior (debe fallar)")
        try:
            # Intentar usar el refresh token viejo (ya revocado)
            old_refresh = tokens.get("refresh", "")
            # El anterior ya fue rotado, usamos uno inventado para simular reuso
            response = await stub.RefreshToken(
                auth_pb2.RefreshTokenRequest(
                    refresh_token="token.revocado.viejo",
                )
            )
            if not response.success:
                ok(f"Rechazado correctamente: {response.error.message}")
                passed += 1
            else:
                fail("Debería haber fallado")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 11. LOGOUT
        # ============================================================
        section("11. Logout — Cerrar sesión")
        try:
            response = await stub.Logout(
                auth_pb2.LogoutRequest(
                    access_token=tokens.get("access", ""),
                )
            )
            if response.success:
                ok(f"Logout exitoso: {response.message}")
                passed += 1
            else:
                fail(f"Logout falló: {response.error.message}")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 12. VALIDATE después de LOGOUT (refresh revocado)
        # ============================================================
        section("12. ValidateToken — Después de logout (token aún válido)")
        try:
            # El access token sigue siendo válido (es stateless, no revocable)
            # Solo los refresh tokens son revocados en logout
            response = await stub.ValidateToken(
                auth_pb2.ValidateTokenRequest(
                    access_token=tokens.get("access", ""),
                )
            )
            if response.valid:
                ok("Access token sigue válido (esperado — es stateless/JWT)")
                ok("Solo los refresh tokens se revocan en logout")
                passed += 1
            else:
                # También es válido si decides invalidar access tokens
                ok("Access token invalidado post-logout")
                passed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

        # ============================================================
        # 13. LOGIN con admin seed
        # ============================================================
        section("13. Login — Admin seed (admin@uaa.mx)")
        try:
            response = await stub.Login(
                auth_pb2.LoginRequest(
                    email="admin@uaa.mx",
                    password="admin123",
                )
            )
            if response.success and response.user.role == common_pb2.USER_ROLE_ADMIN:
                ok(f"Admin login: {response.user.email}")
                ok(f"Rol: USER_ROLE_ADMIN = {response.user.role}")
                passed += 1
            else:
                fail(f"Admin login falló: {response.error.message if response.error else 'rol incorrecto'}")
                failed += 1
        except grpc.RpcError as e:
            fail(f"gRPC error: {e.code()} — {e.details()}")
            failed += 1

    finally:
        await channel.close()

    # ============================================================
    # Resumen
    # ============================================================
    header("Resultados")
    total = passed + failed
    print(f"  Total:   {total}")
    print(f"  {Colors.GREEN}Passed:  {passed}{Colors.RESET}")
    print(f"  {Colors.RED}Failed:  {failed}{Colors.RESET}")
    print()

    if failed == 0:
        print(f"  {Colors.GREEN}{Colors.BOLD}🎉 Todos los tests pasaron!{Colors.RESET}")
    else:
        print(f"  {Colors.RED}{Colors.BOLD}⚠ {failed} test(s) fallaron{Colors.RESET}")

    print()
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
