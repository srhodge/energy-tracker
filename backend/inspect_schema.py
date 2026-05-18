from sqlalchemy import create_engine, inspect
import sys
sys.path.insert(0, ".")
from app.config import settings
engine = create_engine(settings.database_url)
inspector = inspect(engine)
for table in sorted(inspector.get_table_names()):
    print(f"TABLE: {table}")
    for col in inspector.get_columns(table):
        print(f'  {col["name"]:40s} {str(col["type"]):30s} nullable={col["nullable"]}')
    print()
