"""Configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

MATCH_THRESHOLD: int = int(os.environ.get("MATCH_THRESHOLD", "80"))
INPUT_DIR: str = os.environ.get("INPUT_DIR", "input")
OUTPUT_DIR: str = os.environ.get("OUTPUT_DIR", "output")
GMAIL_USER: str = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD: str = os.environ.get("GMAIL_APP_PASSWORD", "")

EMAIL_SUBJECT: str = "Certificado de Participación - Hackathon Tech4Future Hack"
EMAIL_BODY: str = """\
Hola {nombre},

Gracias por ser parte del Hackathon Tech4Future Hack, organizado por el
Hub Boliviano de Inteligencia Artificial junto a Microsoft Learn Student
Ambassadors (Cochabamba).

Tu participación en este evento, enfocado en desarrollar soluciones
innovadoras con Inteligencia Artificial orientadas a los Objetivos de
Desarrollo Sostenible (ODS) de las Naciones Unidas en los ejes de Salud,
Educación y Medio Ambiente, fue muy valiosa.

Adjunto encontrarás tu certificado de participación.

¡Esperamos verte en futuros eventos!

Saludos cordiales,
Hub Boliviano de Inteligencia Artificial
Microsoft Learn Student Ambassadors - Cochabamba
"""
