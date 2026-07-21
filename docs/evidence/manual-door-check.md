# Check manual de puerta

Esta rama implementa un recordatorio diario local para confirmar que la puerta principal quedó cerrada. No controla una alarma ni una cerradura. El estado debe persistir en NVS, mostrar la hora de confirmación y volver a pendiente cuando cambia el día después de sincronizar NTP.
