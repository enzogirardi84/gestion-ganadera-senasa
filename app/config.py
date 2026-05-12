import os
from datetime import date

class Config:
    DB_NAME = os.environ.get("DB_NAME", "gestion_bovinos_senasa.db")
    BACKUP_DIR = os.environ.get("BACKUP_DIR", "backups")
    APP_NAME = "Gestion Ganadera SENASA"
    VERSION = "3.0.0"

    PROVINCIAS = [
        "Buenos Aires", "CABA", "Catamarca", "Chaco", "Chubut", "Cordoba",
        "Corrientes", "Entre Rios", "Formosa", "Jujuy", "La Pampa", "La Rioja",
        "Mendoza", "Misiones", "Neuquen", "Rio Negro", "Salta", "San Juan",
        "San Luis", "Santa Cruz", "Santa Fe", "Santiago del Estero",
        "Tierra del Fuego", "Tucuman"
    ]

    RAZAS_BOVINAS = [
        "Angus", "Hereford", "Braford", "Brangus", "Holando",
        "Criolla", "Charolais", "Limousin", "Salers", "Otra"
    ]

    CATEGORIAS = ["Ternero/a", "Vaquillona", "Novillo", "Vaca", "Toro"]

    TIPOS_ID = ["Visual (Tradicional)", "RFID (Electronica)", "Bolo Ruminal"]

    ESTADOS_ANIMAL = ["Activo", "Mortandad", "Venta", "Cambio de Dueno"]

    EVENTOS_SANIDAD = [
        "Aftosa (Campania)", "Carbunclo", "Desparasitacion",
        "Tratamiento Clinico"
    ]

    ENFERMEDADES_DENUNCIABLES = [
        "Carbunclo", "Tuberculosis", "Brucelosis", "Aftosa", "Rabia"
    ]

    ESTADOS_CUMPLIMIENTO = ["Cumplido", "Pendiente", "En Proceso", "No Aplica"]