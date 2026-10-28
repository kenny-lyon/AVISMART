"""Las pruebas nunca envían correos reales: el SMTP del .env queda desactivado (load_dotenv no sobreescribe esto)."""
import os

os.environ["SMTP_HOST"] = ""
