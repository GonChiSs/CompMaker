# CompMaker

CompMaker es una aplicacion de escritorio para League of Legends enfocada en composiciones, sinergias, matchups y build crafting. Combina datos del parche actual, informacion de meta y un chat local con LLM para ayudar a tomar decisiones dentro de la partida y durante draft.

## Que hace

- Modo `01 ASISTENTE`: ayuda a construir composiciones y analizar sinergias.
- Modo `02 GENERADOR`: genera composiciones por arquetipo.
- Modo `03 RANDOM`: seleccion aleatoria de campeones.
- Modo `04 SIMULADOR`: flujo de draft/simulacion.
- Modo `05 GUARDADAS`: guardar y cargar composiciones.
- Modo `06 TIERLIST`: consulta de tierlists.
- Modo `07 PIZARRA`: pizarra tactica para planificacion visual.
- Modo `08 MATCHUP`: informacion de matchups y counters.
- Modo `09 ITEMIZAR`: analisis de build meta, runas y chat con `Comp AI`.

## Tecnologias principales

- `Python 3.12`
- `PyQt6` para la interfaz
- `requests` y `BeautifulSoup` para datos externos
- `Ollama` para el chat local con LLM
- `PyInstaller` + `Inno Setup` para generar el instalador de Windows

## Estructura

- [lol_comp_builder/main.py](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/lol_comp_builder/main.py): punto de entrada de la app.
- [lol_comp_builder/ui](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/lol_comp_builder/ui): modos, ventanas y widgets.
- [lol_comp_builder/logic](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/lol_comp_builder/logic): logica de negocio, carga de datos, meta, optimizer y chat.
- [lol_comp_builder/data](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/lol_comp_builder/data): datos runtime, cache y snapshots de contexto.
- [lol_comp_builder/tests](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/lol_comp_builder/tests): tests automatizados.
- [Installer](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/Installer): instaladores generados.

## Requisitos

- Windows
- Python 3.12 recomendado
- Ollama instalado para usar el chat local
- Inno Setup si quieres compilar el setup

Dependencias Python en [requirements.txt](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/lol_comp_builder/requirements.txt).

## Arranque en desarrollo

Desde la carpeta [lol_comp_builder](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/lol_comp_builder):

```powershell
python -m pip install -r requirements.txt
python main.py
```

La app prepara datos runtime al inicio e intenta arrancar `Ollama` en segundo plano si esta instalado.

## Compilar ejecutable y setup

Para generar la build e instalador de Windows:

```powershell
cd lol_comp_builder
cmd /c build_setup.bat
```

Script principal:

- [build_setup.bat](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/lol_comp_builder/build_setup.bat)

Configuracion del instalador:

- [installer.iss](C:/Users/gonza/Desktop/Archivos/Proyectos/CompMaker/lol_comp_builder/installer.iss)

## Chat y contexto del parche

El modo `09 ITEMIZAR` usa un flujo mixto:

- build meta y runas del parche actual
- contexto compacto persistente por parche
- contexto minimo por campeon/rol
- LLM local con streaming para responder mas rapido

Los snapshots se guardan automaticamente en:

- `lol_comp_builder/data/context_cache/patch_context_min_<patch>.json`
- `lol_comp_builder/data/context_cache/champion_context/`

Esto reduce el coste de reconstruir contexto en cada mensaje y mejora la latencia del chat.

## Tests

Ejecutar la suite principal del modo 9:

```powershell
python -m pytest lol_comp_builder\tests\test_itemizar_meta_and_models.py -q
```

## Estado actual

- Chat local `Comp AI` integrado con Ollama
- Build meta y runas visibles en UI
- Context cache por parche y por campeon/rol
- Setup de Windows versionado en la carpeta `Installer`

