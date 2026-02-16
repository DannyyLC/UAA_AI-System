"""Cliente gRPC para Auth Service."""

import os
from typing import Optional

import grpc

from src.generated import auth_pb2, auth_pb2_grpc
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class AuthGRPCClient:
    """Cliente gRPC para comunicación con Auth Service."""

    def __init__(self):
        """Inicializa el cliente gRPC."""
        auth_host = os.getenv("AUTH_GRPC_HOST", "localhost")
        auth_port = os.getenv("AUTH_GRPC_PORT", "50051")
        self.address = f"{auth_host}:{auth_port}"
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[auth_pb2_grpc.AuthServiceStub] = None

    async def connect(self):
        """Establece la conexión con el servicio gRPC."""
        try:
            self.channel = grpc.aio.insecure_channel(self.address)
            self.stub = auth_pb2_grpc.AuthServiceStub(self.channel)
            logger.info(f"Conectado a Auth Service en {self.address}")
        except Exception as e:
            logger.error(f"Error conectando a Auth Service: {e}")
            raise

    async def close(self):
        """Cierra la conexión gRPC."""
        if self.channel:
            await self.channel.close()
            logger.info("Conexión con Auth Service cerrada")

    async def register(
        self, email: str, password: str, full_name: str
    ) -> auth_pb2.RegisterResponse:
        """
        Registra un nuevo usuario.

        Args:
            email: Email del usuario
            password: Contraseña del usuario
            full_name: Nombre completo del usuario

        Returns:
            RegisterResponse con información del usuario y token
        """
        if not self.stub:
            await self.connect()

        try:
            request = auth_pb2.RegisterRequest(email=email, password=password, name=full_name)
            response = await self.stub.Register(request)
            logger.info(f"Usuario registrado exitosamente: {email}")
            return response
        except grpc.RpcError as e:
            logger.error(f"Error en registro: {e.code()} - {e.details()}")
            raise

    async def login(self, email: str, password: str) -> auth_pb2.LoginResponse:
        """
        Autentica un usuario.

        Args:
            email: Email del usuario
            password: Contraseña del usuario

        Returns:
            LoginResponse con información del usuario y token
        """
        if not self.stub:
            await self.connect()

        try:
            request = auth_pb2.LoginRequest(email=email, password=password)
            response = await self.stub.Login(request)
            logger.info(f"Usuario autenticado exitosamente: {email}")
            return response
        except grpc.RpcError as e:
            logger.error(f"Error en login: {e.code()} - {e.details()}")
            raise

    async def validate_token(self, token: str) -> auth_pb2.ValidateTokenResponse:
        """
        Valida un token JWT.

        Args:
            token: Token JWT a validar

        Returns:
            ValidateTokenResponse con información del usuario si el token es válido
        """
        if not self.stub:
            await self.connect()

        try:
            request = auth_pb2.ValidateTokenRequest(access_token=token)
            response = await self.stub.ValidateToken(request)
            return response
        except grpc.RpcError as e:
            logger.error(f"Error validando token: {e.code()} - {e.details()}")
            raise

    async def logout(self, token: str) -> auth_pb2.LogoutResponse:
        """
        Cierra la sesión de un usuario.

        Args:
            token: Token JWT de la sesión a cerrar

        Returns:
            LogoutResponse confirmando el cierre de sesión
        """
        if not self.stub:
            await self.connect()

        try:
            request = auth_pb2.LogoutRequest(access_token=token)
            response = await self.stub.Logout(request)
            logger.info("Sesión cerrada exitosamente")
            return response
        except grpc.RpcError as e:
            logger.error(f"Error en logout: {e.code()} - {e.details()}")
            raise

    async def refresh_token(self, token: str) -> auth_pb2.RefreshTokenResponse:
        """
        Renueva un token JWT.

        Args:
            token: Token JWT actual

        Returns:
            RefreshTokenResponse con el nuevo token
        """
        if not self.stub:
            await self.connect()

        try:
            request = auth_pb2.RefreshTokenRequest(refresh_token=token)
            response = await self.stub.RefreshToken(request)
            logger.info("Token renovado exitosamente")
            return response
        except grpc.RpcError as e:
            logger.error(f"Error renovando token: {e.code()} - {e.details()}")
            raise


# Instancia global del cliente
auth_client = AuthGRPCClient()
