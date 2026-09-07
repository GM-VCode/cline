# tools — ferramentas que rodam separadas do modelo
#
#  validate.py -> gate de validação (compileall + unittest + diff)
#  doctor.py   -> diagnóstico do ambiente (class ModelDoctor)
#  logger.py   -> class AppLogger (logging com níveis, logs/)
#
#  Uso (a partir da raiz do projeto):
#    python tools/validate.py
#    python tools/doctor.py