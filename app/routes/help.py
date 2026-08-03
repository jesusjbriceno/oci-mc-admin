"""Help page with custom Minecraft commands."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templates import _render

router = APIRouter()

# ── Custom commands organized by category ─────────────────────────────────

COMMANDS = {
    "Jugadores": [
        ("list", "Listar jugadores conectados"),
        ("kick <jugador> [razón]", "Expulsar a un jugador"),
        ("ban <jugador>", "Banear a un jugador"),
        ("pardon <jugador>", "Desbanear a un jugador"),
        ("whitelist add <jugador>", "Añadir a whitelist"),
        ("whitelist remove <jugador>", "Quitar de whitelist"),
        ("whitelist reload", "Recargar whitelist"),
        ("whitelist list", "Ver whitelist"),
        ("op <jugador>", "Dar permisos de operador"),
        ("deop <jugador>", "Quitar permisos de operador"),
    ],
    "Mundo": [
        ("time set <hora>", "Cambiar hora (0-24000, day, noon, night, midnight)"),
        ("weather <clear|rain|thunder> [duración]", "Cambiar clima"),
        ("difficulty <peaceful|easy|normal|hard>", "Cambiar dificultad"),
        ("gamemode <survival|creative|adventure|spectator> [jugador]", "Cambiar modo de juego"),
        ("tp <jugador1> <jugador2>", "Teletransportar jugador1 a jugador2"),
        ("tp <jugador> <x> <y> <z>", "Teletransportar a coordenadas"),
        ("setworldspawn <x> <y> <z>", "Establecer spawn del mundo"),
        ("spawnpoint <jugador> <x> <y> <z>", "Establecer spawn de jugador"),
        ("locate <estructura>", "Localizar estructura (village, mansion, etc.)"),
        ("seed", "Ver la semilla del mundo"),
    ],
    "Objetos": [
        ("give <jugador> <item> [cantidad]", "Dar objeto a jugador"),
        ("clear <jugador> [item]", "Limpiar inventario (o un item específico)"),
        ("enchant <jugador> <encantamiento> [nivel]", "Encantar objeto en mano"),
        ("xp add <jugador> <cantidad>", "Añadir experiencia"),
        ("xp set <jugador> <cantidad>", "Establecer experiencia"),
    ],
    "Comunicación": [
        ("say <mensaje>", "Enviar mensaje global"),
        ("tell <jugador> <mensaje>", "Mensaje privado a jugador"),
        ("msg <jugador> <mensaje>", "Alias de tell"),
        ("me <acción>", "Mostrar acción en chat"),
    ],
    "Servidor": [
        ("save-all", "Guardar mundo"),
        ("save-on", "Activar guardado automático"),
        ("save-off", "Desactivar guardado automático"),
        ("save hold", "Pausar guardado (para backups)"),
        ("save resume", "Reanudar guardado"),
        ("stop", "Detener servidor"),
        ("reload", "Recargar configuración"),
    ],
    "Efectos": [
        ("effect give <jugador> <efecto> [duración] [nivel]", "Dar efecto de poción"),
        ("effect clear <jugador> [efecto]", "Quitar efecto(s)"),
        ("particle <partícula> <x> <y> <z>", "Crear partículas"),
        ("playsound <sonido> <jugador>", "Reproducir sonido"),
    ],
    "Bloques": [
        ("fill <x1> <y1> <z1> <x2> <y2> <z2> <bloque>", "Rellenar área con bloque"),
        ("clone <x1> <y1> <z1> <x2> <y2> <z2> <x> <y> <z>", "Copiar área"),
        ("setblock <x> <y> <z> <bloque>", "Colocar bloque"),
        ("summon <entidad> <x> <y> <z>", "Invocar entidad"),
        ("kill <entidad>", "Matar entidad (o @e, @a, @p)"),
    ],
    "DayZ/Rol": [
        ("scoreboard objectives add <nombre> dummy", "Crear marcador"),
        ("scoreboard players set <jugador> <objetivo> <valor>", "Establecer valor"),
        ("scoreboard players add <jugador> <objetivo> <valor>", "Sumar valor"),
        ("tag <jugador> add <etiqueta>", "Añadir etiqueta a jugador"),
        ("tag <jugador> remove <etiqueta>", "Quitar etiqueta"),
        ("execute as <jugador> run <comando>", "Ejecutar como jugador"),
        ("execute at <jugador> run <comando>", "Ejecutar en posición de jugador"),
    ],
    "D&D Builder": [
        ("function dnd/dungeon", "Mazmorra básica 7x7x5 con antorchas"),
        ("function dnd/tower", "Torre de vigilancia 12 bloques con glowstone"),
        ("function dnd/floor", "Suelo plano de 20x20"),
        ("function dnd/wall", "Muro de 10 largo x 5 alto"),
        ("function dnd/fill_small", "Cubo 5x5x5 con piedra"),
        ("function dnd/alcantarillas", "Alcantarilla subterránea 3x3x20"),
        ("function dnd/altar", "Altar con mesa de encantamientos"),
        ("function dnd/biblioteca", "Biblioteca 11x6x7"),
        ("function dnd/bosque_gris", "Bosque con musgo y robles pálidos 20x20"),
        ("function dnd/bridge", "Puente de piedra 15 bloques con barandillas"),
        ("function dnd/caminos", "Camino 30 bloques con farolas"),
        ("function dnd/campos", "Campos de cultivo 11x11 con agua y vallas"),
        ("function dnd/casas", "Casa de madera 7x5x6"),
        ("function dnd/cementerio", "Cementerio 14x9 con tumbas"),
        ("function dnd/cuartel", "Cuartel 9x4x7"),
        ("function dnd/el_cuervo_cansado", "Posada El Cuervo Cansado 11x5x8"),
        ("function dnd/mercado", "Mercado 13x11 con techo"),
        ("function dnd/murallas", "Murallas de 30 bloques con almenas"),
        ("function dnd/pit_trap", "Foso trampa 5x5 con lava"),
        ("function dnd/plaza_central", "Plaza central 15x15 con fuente"),
        ("function dnd/puerta_principal", "Puerta principal de ciudad 8 bloques"),
        ("function dnd/tavern", "Taberna 7x4x5"),
        ("function dnd/throne_room", "Sala del trono 9x5x7"),
    ],
}


@router.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    return _render(request, "help.html", {"active": "help", "commands": COMMANDS})
