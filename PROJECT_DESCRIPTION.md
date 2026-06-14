# Descripcion del Proyecto

CompMaker es una herramienta de escritorio para jugadores de League of Legends que centraliza composiciones, sinergias, tierlists, matchups, builds y apoyo conversacional con IA local.

El objetivo del proyecto es ofrecer una experiencia practica para preparar draft, analizar picks y ajustar builds sin depender de servicios cloud. Para ello combina:

- una interfaz PyQt6 con varios modos especializados
- datos del parche actual y de la meta
- analisis local de composiciones y matchups
- un asistente conversacional con modelos locales mediante Ollama

Su parte mas avanzada es el modo `09 ITEMIZAR`, que muestra la build meta y las runas mas usadas de una combinacion campeon/rol, y permite conversar con `Comp AI` para preguntar por matchups, counters, cambios de build y decisiones de itemizacion. El sistema utiliza snapshots compactos del parche y contexto puntual por campeon para acelerar las respuestas del LLM y mantener coherencia con el meta actual.

En conjunto, CompMaker busca ser una navaja suiza para teoria de draft y toma de decisiones dentro de partida: una app local, visual y orientada a flujo real de juego.
