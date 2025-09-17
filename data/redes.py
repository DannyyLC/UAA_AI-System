redes_respuestas = [
    "Una dirección IP pública es única globalmente en Internet y permite la comunicación entre dispositivos a través de la red mundial, asignada por ISPs. Una dirección IP privada es utilizada únicamente dentro de redes locales (192.168.x.x, 10.x.x.x, 172.16-31.x.x) y no es enrutable directamente en Internet, permitiendo múltiples redes usar los mismos rangos privados.",
    
    "El modelo OSI (Open Systems Interconnection) es un marco conceptual de 7 capas para estandarizar las comunicaciones de red: 1) Física (transmisión de bits), 2) Enlace de datos (detección de errores), 3) Red (enrutamiento), 4) Transporte (entrega confiable), 5) Sesión (gestión de conexiones), 6) Presentación (codificación/cifrado), 7) Aplicación (servicios de usuario final).",
    
    "TCP (Transmission Control Protocol) es un protocolo confiable orientado a conexión que garantiza la entrega ordenada de datos mediante confirmaciones, control de flujo y retransmisión. UDP (User Datagram Protocol) es un protocolo sin conexión, más rápido pero sin garantías de entrega, ideal para aplicaciones en tiempo real como streaming o juegos donde la velocidad es prioritaria sobre la confiabilidad.",
    
    "Una máscara de subred es un número de 32 bits que define qué parte de una dirección IP corresponde a la red y cuál al host. Permite dividir redes en subredes más pequeñas para optimizar el uso de direcciones IP, mejorar la seguridad y reducir el tráfico de broadcast. Por ejemplo, 255.255.255.0 (/24) indica que los primeros 24 bits identifican la red.",
    
    "ARP (Address Resolution Protocol) mapea direcciones IP a direcciones MAC en redes locales. Cuando un dispositivo necesita comunicarse con otro en la misma subred, envía una solicitud ARP broadcast preguntando 'quién tiene esta IP', y el dispositivo correspondiente responde con su dirección MAC, permitiendo la comunicación a nivel de enlace de datos.",
    
    "LAN (Local Area Network) cubre un área geográfica pequeña como oficinas o edificios con alta velocidad y baja latencia. MAN (Metropolitan Area Network) conecta múltiples LANs en una ciudad o área metropolitana. WAN (Wide Area Network) conecta redes a través de grandes distancias geográficas, típicamente usando enlaces de telecomunicaciones públicos como Internet.",
    
    "DNS (Domain Name System) es el sistema que traduce nombres de dominio legibles (google.com) a direcciones IP numéricas. Funciona mediante una jerarquía de servidores: servidores raíz, TLD (Top Level Domain), autoritativos y recursivos. Cuando solicitas un dominio, tu resolver consulta esta jerarquía hasta obtener la IP correspondiente, almacenando resultados en caché para eficiencia.",
    
    "Los ataques de spoofing se detectan mediante análisis de patrones de tráfico anómalos, verificación de coherencia en headers de paquetes, y monitoring de direcciones MAC/IP duplicadas. Se previenen implementando autenticación fuerte, validación de origen, filtrado de paquetes, técnicas como reverse path filtering, y usando protocolos seguros que incluyan verificación de integridad y autenticidad.",
    
    "NAT (Network Address Translation) traduce direcciones IP privadas internas a públicas para acceso a Internet. En redes domésticas, el router mantiene una tabla de traducción que mapea direcciones/puertos internos con externos, permitiendo que múltiples dispositivos privados compartan una sola IP pública, proporcionando seguridad adicional al ocultar la topología interna.",
    
    "HTTP (HyperText Transfer Protocol) transmite datos sin cifrado, siendo vulnerable a interceptación y modificación. HTTPS (HTTP Secure) añade una capa de cifrado TLS/SSL que asegura la confidencialidad, integridad y autenticación de los datos transmitidos, protegiendo contra ataques man-in-the-middle y garantizando que el servidor es quien dice ser mediante certificados digitales."
]