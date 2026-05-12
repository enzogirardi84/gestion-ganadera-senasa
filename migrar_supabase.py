import subprocess
import sys

print("="*60)
print("  MIGRACION A SUPABASE")
print("="*60)
print()
print("Paso 1: Abri https://supabase.com/dashboard/project/tfdgaxowacbxqtuvhhdp")
print("Paso 2: Hace clic en SQL Editor (menu izquierdo)")
print("Paso 3: Borra cualquier texto que haya")
print("Paso 4: Copia TODO el contenido del archivo:")
print()
print("   C:\\sanidad\\sql_para_supabase.sql")
print()
print("Paso 5: Pegalo en el editor (Ctrl+V)")
print("Paso 6: Hace clic en RUN (o Ctrl+Enter)")
print()
print("="*60)

input("Presiona Enter para abrir la carpeta con el archivo...")

subprocess.Popen(['explorer', '/select,', 'C:\\sanidad\\sql_para_supabase.sql'])
