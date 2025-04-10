"""
Configuration for Supabase authentication.
This file stores the Supabase connection details.
"""

import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Supabase Configuration
# Tenta carregar das variáveis de ambiente ou usa os valores padrão apenas para desenvolvimento
SUPABASE_URL = os.getenv('SUPABASE_URL', "https://ylbojqpbgbtkydoyfmnh.supabase.co") 
SUPABASE_KEY = os.getenv('SUPABASE_KEY', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlsYm9qcXBiZ2J0a3lkb3lmbW5oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQzMjMyOTMsImV4cCI6MjA1OTg5OTI5M30.f8Za3HktzQYmQB5q630gGpG1hGqCUupeZH4V8T0LGrc")
