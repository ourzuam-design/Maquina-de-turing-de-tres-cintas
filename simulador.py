from collections import namedtuple

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    tk = ttk = messagebox = None

BLANCO = "□"
CUALQUIERA = "?"
IGUAL = "="
ACEPTA = "q_accept"
RECHAZA = "q_reject"

LIMITE_NUMERO = 500
LIMITE_CONTEO = 200_000
LIMITE_PASOS = 5_000_000
CELDA = 36


def leer_entero(texto):
    texto = texto.strip()
    cuerpo = texto[1:] if texto.startswith("-") else texto

    if not cuerpo.isdecimal():
        raise ValueError(
            "Introduce numeros enteros (pueden llevar signo -)."
        )

    return int(texto)


def signo_unario(n):
    return "-" if n < 0 else ""


def calcular(a, b, op):
    if op == "+":
        return a + b, None
    if op == "-":
        return a - b, None
    if op == "*":
        return a * b, None

    cociente = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        cociente = -cociente

    return cociente, a - cociente * b


def entrada_unaria(a, op, b):
    return (
        signo_unario(a) + "1" * abs(a)
        + "#" + op + "#"
        + signo_unario(b) + "1" * abs(b)
    )


class Cinta:
    def __init__(self):
        self.celdas = {}
        self.cabezal = 0

    def leer(self):
        return self.celdas.get(self.cabezal, BLANCO)

    def leer_posicion(self, posicion):
        return self.celdas.get(posicion, BLANCO)

    def escribir(self, simbolo):
        if simbolo == BLANCO:
            self.celdas.pop(self.cabezal, None)
        else:
            self.celdas[self.cabezal] = simbolo

    def mover(self, direccion):
        if direccion == "R":
            self.cabezal += 1
        elif direccion == "L":
            self.cabezal -= 1
        elif direccion != "S":
            raise ValueError(f"Movimiento desconocido: {direccion}")

    def cargar(self, texto):
        self.celdas.clear()
        self.cabezal = 0
        for i, simbolo in enumerate(texto):
            if simbolo != BLANCO:
                self.celdas[i] = simbolo

    def limites(self):
        if not self.celdas:
            return None
        return min(self.celdas), max(self.celdas)

    def texto(self):
        lim = self.limites()
        if lim is None:
            return ""
        return "".join(
            self.celdas.get(i, BLANCO) for i in range(lim[0], lim[1] + 1)
        )


def valor_de_cinta(cinta):
    signo = cinta.leer_posicion(0)
    unos = 0
    while cinta.leer_posicion(unos + 1) == "1":
        unos += 1

    if signo == "0":
        return 0 if unos == 0 else None
    if signo == "+":
        return unos
    if signo == "-":
        return -unos
    return None


Regla = namedtuple("Regla", "estado lee escribe mueve siguiente descripcion")


class Constructor:

    def __init__(self):
        self.reglas = []

    def r(self, estado, lee, siguiente, escribe, mueve, texto):
        assert len(lee) == len(escribe) == len(mueve) == 3, (estado, lee)
        self.reglas.append(
            Regla(estado, tuple(lee), tuple(escribe), tuple(mueve),
                  siguiente, texto)
        )


def _pat(k, s):
    return "".join(s if i == k else CUALQUIERA for i in range(3))


def _esc(k, s):
    return "".join(s if i == k else IGUAL for i in range(3))


def _mov(k, m):
    return "".join(m if i == k else "S" for i in range(3))


def _opuesto(signo):
    return "-" if signo == "+" else "+"


def _agregar_fin(c, k, pref, salida, mov_salida, ceros="+-", blancos=False):
    L, C, Z = f"{pref}_L", f"{pref}_C", f"{pref}_Z"
    n = k + 1
    for s in ("1", BLANCO) if blancos else ("1",):
        c.r(L, _pat(k, s), L, "===", _mov(k, "L"),
            f"Retrocede en C{n} buscando la celda del signo")
    for s in "+-":
        c.r(L, _pat(k, s), C, "===", _mov(k, "R"),
            f"Encontró el signo en C{n}: mira si hay dígitos")
    c.r(C, _pat(k, "1"), salida, "===", mov_salida,
        f"C{n} tiene dígitos: el signo se queda")
    if ceros:
        c.r(C, _pat(k, BLANCO), Z, "===", _mov(k, "L"),
            f"C{n} no tiene dígitos: el valor es 0")
        for s in ceros:
            c.r(Z, _pat(k, s), salida, _esc(k, "0"), mov_salida,
                f"Escribe 0 en la celda del signo de C{n}")


def _copiar_a(c):
    c.r("q0", "-??", "copiaA", "=-=", "RRS",
        "A es negativo: guarda '-' en la celda 0 de C2 y salta el signo en C1")
    c.r("q0", "1??", "copiaA", "=+=", "SRS",
        "A es positivo: guarda '+' en la celda 0 de C2")
    c.r("q0", "#??", "copiaA", "=+=", "SRS",
        "A es 0: guarda '+' en la celda 0 de C2")
    c.r("copiaA", "1??", "copiaA", "=1=", "RRS", "Copia un 1 de A a C2")
    c.r("copiaA", "#??", "retroA", "===", "SLS", "Terminó A: rebobina C2")
    c.r("retroA", "?1?", "retroA", "===", "SLS", "Rebobina C2 hacia su signo")
    for s in "+-":
        c.r("retroA", f"?{s}?", f"op{s}", "===", "RRS",
            f"C2 llegó a su signo ({s}); C1 pasa al operador")


def _tabla_suma_resta(op):
    resta = op == "-"
    c = Constructor()
    _copiar_a(c)

    con_menos = "+" if resta else "-"
    sin_signo = "-" if resta else "+"

    for s in "+-":
        c.r(f"op{s}", f"{op}??", f"hash{s}", "===", "RSS",
            f"Lee el operador '{op}'")
        c.r(f"hash{s}", "#??", f"signoB{s}", "===", "RSS",
            "Salta el '#' antes de B")
        c.r(f"signoB{s}", "-??", f"cmp{s}{con_menos}", "===", "RSS",
            f"B lleva '-': su signo efectivo es {con_menos}")
        for vacio_o_uno in ("1", BLANCO):
            c.r(f"signoB{s}", f"{vacio_o_uno}??", f"cmp{s}{sin_signo}", "===",
                "SSS", f"B sin signo: su signo efectivo es {sin_signo}")

    for s in "+-":
        for e in "+-":
            est = f"cmp{s}{e}"
            if s == e:
                c.r(est, "???", "sumaA", f"=={s}", "SSR",
                    f"Mismos signos ({s}): escribe el signo en C3")
            else:
                c.r(est, "11?", est, "X□=", "RRS",
                    "Cancela un 1 de B (X) contra un 1 de A (lo borra de C2)")
                c.r(est, f"{BLANCO}1?", "quedaA", f"=={s}", "SSR",
                    f"B se acabó y sobra A: el signo es el de A ({s})")
                c.r(est, f"1{BLANCO}?", "quedaB", f"=={e}", "SSR",
                    f"A se acabó y sobra B: el signo es el de B ({e})")
                c.r(est, f"{BLANCO}{BLANCO}?", ACEPTA, "==0", "SSS",
                    "Se cancelaron por completo: el resultado es 0")

    c.r("sumaA", "?1?", "sumaA", "==1", "SRR", "Copia un 1 de A a C3")
    c.r("sumaA", f"?{BLANCO}?", "sumaB", "===", "SSS", "Terminó A; sigue B")
    c.r("sumaB", "1??", "sumaB", "==1", "RSR", "Copia un 1 de B a C3")
    c.r("sumaB", f"{BLANCO}??", "fin3_L", "===", "SSL",
        "Terminó B: revisa el resultado")

    c.r("quedaA", "?1?", "quedaA", "==1", "SRR", "Copia a C3 lo que sobra de A")
    c.r("quedaA", f"?{BLANCO}?", "fin3_L", "===", "SSL",
        "Terminó: revisa el resultado")
    c.r("quedaB", "1??", "quedaB", "==1", "RSR", "Copia a C3 lo que sobra de B")
    c.r("quedaB", f"{BLANCO}??", "fin3_L", "===", "SSL",
        "Terminó: revisa el resultado")

    _agregar_fin(c, 2, "fin3", ACEPTA, "SSS", ceros="" if resta else "+")
    return c.reglas


def _tabla_multiplicacion():
    c = Constructor()
    _copiar_a(c)

    for s in "+-":
        c.r(f"op{s}", "*??", f"hash{s}", "===", "RSS", "Lee el operador '*'")
        c.r(f"hash{s}", "#??", f"signoB{s}", "===", "RSS",
            "Salta el '#' antes de B")
        c.r(f"signoB{s}", "-??", "mulB", f"=={_opuesto(s)}", "RSR",
            f"B lleva '-': el producto tiene signo {_opuesto(s)} (se escribe en C3)")
        for vacio_o_uno in ("1", BLANCO):
            c.r(f"signoB{s}", f"{vacio_o_uno}??", "mulB", f"=={s}", "SSR",
                f"B sin signo: el producto tiene signo {s} (se escribe en C3)")

    c.r("mulB", "1??", "mulA", "X==", "RSS",
        "Toma un 1 de B (lo marca X): va a copiar A completo")
    c.r("mulB", f"{BLANCO}??", "fin3_L", "===", "SSL",
        "No quedan 1 en B: revisa el resultado")
    c.r("mulA", "?1?", "mulA", "==1", "SRR", "Copia un 1 de A a C3")
    c.r("mulA", f"?{BLANCO}?", "mulR", "===", "SLS",
        "Terminó esta copia de A: rebobina C2")
    c.r("mulR", "?1?", "mulR", "===", "SLS", "Rebobina C2 hacia su signo")
    for s in "+-":
        c.r("mulR", f"?{s}?", "mulB", "===", "SRS",
            "C2 de nuevo al inicio de A; vuelve a B")

    _agregar_fin(c, 2, "fin3", ACEPTA, "SSS")
    return c.reglas


def _tabla_division():
    c = Constructor()
    c.r("q0", "-??", "saltaA-", "=-=", "RRS",
        "A es negativo: guarda '-' en C2 (signo del residuo) y salta el signo")
    c.r("q0", "1??", "saltaA+", "=+=", "SRS",
        "A es positivo: guarda '+' en C2 (signo del residuo)")
    c.r("q0", "#??", "saltaA+", "=+=", "SRS",
        "A es 0: guarda '+' en C2")

    for s in "+-":
        c.r(f"saltaA{s}", "1??", f"saltaA{s}", "===", "RSS",
            "Pasa por encima de los 1 de A")
        c.r(f"saltaA{s}", "#??", f"op{s}", "===", "RSS", "Fin de A")
        c.r(f"op{s}", "/??", f"hash{s}", "===", "RSS", "Lee el operador '/'")
        c.r(f"hash{s}", "#??", f"signoB{s}", "===", "RSS",
            "Salta el '#' antes de B")
        c.r(f"signoB{s}", "-??", "primB", f"=={_opuesto(s)}", "RSR",
            f"B lleva '-': el cociente tiene signo {_opuesto(s)} (se escribe en C3)")
        c.r(f"signoB{s}", "1??", "primB", f"=={s}", "SSR",
            f"B sin signo: el cociente tiene signo {s} (se escribe en C3)")
        c.r(f"signoB{s}", f"{BLANCO}??", RECHAZA, "===", "SSS",
            "B es 0: no se puede dividir entre cero, rechaza")

    c.r("primB", "1??", "copiaB", "=1=", "RRS",
        "Copia el primer 1 de B a C2 (plantilla del grupo)")
    c.r("copiaB", "1??", "copiaB", "=1=", "RRS", "Copia un 1 de B a C2")
    c.r("copiaB", f"{BLANCO}??", "retro2", "===", "SLS",
        "Terminó B: rebobina C2")
    c.r("retro2", "?1?", "retro2", "===", "SLS", "Rebobina C2 hacia su signo")
    for s in "+-":
        c.r("retro2", f"?{s}?", "retro1", "===", "LRS",
            "C2 en el primer 1 de la plantilla; C1 empieza a rebobinar")
    c.r("retro1", f"{BLANCO}??", "ini1", "===", "RSS",
        "C1 llegó al borde izquierdo")
    c.r("retro1", "???", "retro1", "===", "LSS", "Rebobina C1")
    c.r("ini1", "-??", "div", "===", "RSS", "Salta el signo de A")
    c.r("ini1", "1??", "div", "===", "SSS", "Empieza a dividir")
    c.r("ini1", "#??", "div", "===", "SSS", "A es 0: empieza a dividir")

    c.r("div", "11?", "div", "X==", "RRS",
        "Quita un 1 de A (X) con un 1 de la plantilla de C2")
    c.r("div", f"?{BLANCO}?", "retroQ", "==1", "SLR",
        "Grupo completo: suma un 1 al cociente (C3) y rebobina la plantilla")
    c.r("div", "#1?", "borra", "===", "SSS",
        "A se acabó a mitad de grupo: lo consumido en C2 es el residuo")
    c.r("retroQ", "?1?", "retroQ", "===", "SLS", "Rebobina la plantilla de C2")
    for s in "+-":
        c.r("retroQ", f"?{s}?", "div", "===", "SRS",
            "Plantilla lista para otro grupo")
    c.r("borra", "?1?", "borra", "=□=", "SRS",
        "Borra de C2 la parte de la plantilla que no se usó")
    c.r("borra", f"?{BLANCO}?", "fin2_L", "===", "SLS",
        "Residuo listo: revisa C2")

    _agregar_fin(c, 1, "fin2", "fin3_L", "SSL", blancos=True)
    _agregar_fin(c, 2, "fin3", ACEPTA, "SSS")
    return c.reglas


def _numerar(reglas):
    nombres = {}
    for r in reglas:
        if r.estado not in nombres:
            nombres[r.estado] = f"q{len(nombres)}"

    def nuevo(estado):
        return estado if estado in (ACEPTA, RECHAZA) else nombres[estado]

    return [
        r._replace(estado=nuevo(r.estado), siguiente=nuevo(r.siguiente))
        for r in reglas
    ]


def construir_tabla(op):
    if op in ("+", "-"):
        reglas = _tabla_suma_resta(op)
    elif op == "*":
        reglas = _tabla_multiplicacion()
    elif op == "/":
        reglas = _tabla_division()
    else:
        raise ValueError(f"Operacion desconocida: {op}")
    return _numerar(reglas)


Paso = namedtuple("Paso", "numero antes lecturas indice regla")


class Maquina:

    def __init__(self, op, entrada, reglas=None):
        self.op = op
        self.reglas = reglas if reglas is not None else construir_tabla(op)
        self.cintas = [Cinta(), Cinta(), Cinta()]
        self.cintas[0].cargar(entrada)
        self.estado = "q0"
        self.pasos = 0
        self.terminada = False
        self.aceptada = False
        self.motivo = ""

        self.por_estado = {}
        for i, regla in enumerate(self.reglas):
            self.por_estado.setdefault(regla.estado, []).append(i)
        for lista in self.por_estado.values():
            lista.sort(key=lambda i: self.reglas[i].lee.count(CUALQUIERA))

    def buscar(self, lecturas):
        for i in self.por_estado.get(self.estado, ()):
            lee = self.reglas[i].lee
            if all(p == CUALQUIERA or p == s for p, s in zip(lee, lecturas)):
                return i
        return None

    def paso(self):
        if self.terminada:
            return None

        lecturas = tuple(cinta.leer() for cinta in self.cintas)
        indice = self.buscar(lecturas)

        if indice is None:
            self.terminada = True
            self.motivo = (
                f"No hay regla para el estado {self.estado} "
                f"leyendo {'/'.join(lecturas)}"
            )
            return None

        regla = self.reglas[indice]
        for cinta, escribe, mueve in zip(self.cintas, regla.escribe, regla.mueve):
            if escribe != IGUAL:
                cinta.escribir(escribe)
            cinta.mover(mueve)

        antes = self.estado
        self.estado = regla.siguiente
        self.pasos += 1

        if self.estado == ACEPTA:
            self.terminada = self.aceptada = True
            self.motivo = "La maquina llego a q_accept"
        elif self.estado == RECHAZA:
            self.terminada = True
            self.motivo = "La maquina llego a q_reject"

        return Paso(self.pasos, antes, lecturas, indice, regla)

    def ejecutar(self, limite=LIMITE_PASOS):
        while not self.terminada:
            if self.pasos >= limite:
                return False
            self.paso()
        return True

    def resultado(self):
        if not self.aceptada:
            return None
        valor = valor_de_cinta(self.cintas[2])
        residuo = valor_de_cinta(self.cintas[1]) if self.op == "/" else None
        return valor, residuo


def contar_pasos(op, entrada, limite=LIMITE_CONTEO):
    m = Maquina(op, entrada)
    return m.pasos if m.ejecutar(limite) else None


class MaquinaTuring:
    def __init__(self, ventana):
        self.ventana = ventana
        self.ventana.title("Maquina de Turing de tres cintas")

        self.ventana.update_idletasks()
        ancho = self.ventana.winfo_screenwidth()
        alto = self.ventana.winfo_screenheight()

        ancho_ventana = min(1200, max(760, ancho - 40))
        alto_ventana = min(880, max(640, alto - 80))

        x = max(0, (ancho - ancho_ventana) // 2)
        y = max(0, (alto - alto_ventana) // 2)

        self.ventana.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
        self.ventana.minsize(720, 640)
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar)

        self.maq = None
        self.cintas = [Cinta(), Cinta(), Cinta()]
        self.ejecutando = False
        self.after_id = None
        self.ultima_regla = None
        self.regla_resaltada = None
        self.total_texto = "0"

        self.numero_a = 0
        self.numero_b = 0
        self.op = "+"
        self.resultado_finalizado = False

        self.vistas = [0, 0, 0]
        self.cantidades = [11, 11, 11]
        self.rangos = [(-3, 20)] * 3
        self.arrastre = None
        self.listo = False

        self.crear_interfaz()
        self.listo = True
        self.dibujar_cintas()

    def crear_interfaz(self):
        principal = ttk.Frame(self.ventana, padding=8)
        principal.pack(fill="both", expand=True)

        principal.rowconfigure(2, weight=1)
        principal.columnconfigure(0, weight=1)

        ttk.Label(
            principal,
            text="MAQUINA DE TURING MULTICINTA",
            font=("Arial", 17, "bold")
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        entrada = ttk.LabelFrame(
            principal, text="Datos de entrada", padding=8
        )
        entrada.grid(row=1, column=0, sticky="ew", pady=4)

        for columna in range(8):
            entrada.columnconfigure(columna, weight=1)

        ttk.Label(entrada, text="Numero A").grid(row=0, column=0, padx=3)
        self.a = tk.StringVar(value="7")
        ttk.Entry(
            entrada, textvariable=self.a, width=8
        ).grid(row=1, column=0, padx=3, sticky="ew")

        ttk.Label(entrada, text="Operacion").grid(row=0, column=1, padx=3)
        self.operacion = tk.StringVar(value="+")
        ttk.Combobox(
            entrada,
            textvariable=self.operacion,
            values=["+", "-", "*", "/"],
            state="readonly",
            width=5
        ).grid(row=1, column=1, padx=3, sticky="ew")

        ttk.Label(entrada, text="Numero B").grid(row=0, column=2, padx=3)
        self.b = tk.StringVar(value="3")
        ttk.Entry(
            entrada, textvariable=self.b, width=8
        ).grid(row=1, column=2, padx=3, sticky="ew")

        botones = [
            ("Preparar", self.preparar),
            ("▶ Ejecutar", self.iniciar),
            ("Paso siguiente", self.paso),
            ("⏭ Terminar", self.terminar),
            ("Pausar", self.pausar),
        ]
        for columna, (texto, orden) in enumerate(botones, start=3):
            ttk.Button(entrada, text=texto, command=orden).grid(
                row=1, column=columna, padx=4, sticky="ew"
            )

        barra = ttk.Frame(principal)
        barra.grid(row=2, column=0, sticky="nsew", pady=4)
        barra.columnconfigure(0, weight=1)
        barra.rowconfigure(1, weight=1)

        info = ttk.Frame(barra)
        info.grid(row=0, column=0, sticky="ew", pady=4)
        info.columnconfigure(0, weight=1)

        fila1 = ttk.Frame(info)
        fila1.grid(row=0, column=0, sticky="ew")

        self.estado_label = ttk.Label(
            fila1, text="Estado: q0", font=("Arial", 10, "bold")
        )
        self.estado_label.pack(side="left", padx=5)

        self.pasos_label = ttk.Label(fila1, text="Pasos: 0/0")
        self.pasos_label.pack(side="left", padx=8)

        ttk.Label(fila1, text="Velocidad").pack(side="left", padx=(12, 3))
        self.velocidad = tk.DoubleVar(value=67)
        ttk.Scale(
            fila1,
            from_=1,
            to=100,
            variable=self.velocidad,
            orient="horizontal",
            length=110
        ).pack(side="left", padx=3)

        self.seguir = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            fila1,
            text="Seguir cabezal",
            variable=self.seguir,
            command=self.dibujar_cintas
        ).pack(side="left", padx=12)

        ttk.Button(
            fila1, text="Reiniciar", command=self.reiniciar
        ).pack(side="right", padx=3)

        self.resultado_label = ttk.Label(
            info, text="Resultado: —", font=("Arial", 11, "bold"),
            wraplength=1000, justify="left"
        )
        self.resultado_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)

        self.pestanas = ttk.Notebook(barra)
        self.pestanas.grid(row=1, column=0, sticky="nsew", pady=4)

        pesta_cintas = ttk.Frame(self.pestanas, padding=6)
        pesta_reglas = ttk.Frame(self.pestanas, padding=5)
        pesta_historial = ttk.Frame(self.pestanas, padding=5)

        self.pestanas.add(pesta_cintas, text="Cintas")
        self.pestanas.add(pesta_reglas, text="Tabla de transiciones")
        self.pestanas.add(pesta_historial, text="Historial")

        self.crear_panel_cintas(pesta_cintas)
        self.crear_panel_reglas(pesta_reglas)
        self.crear_panel_historial(pesta_historial)

        ttk.Label(
            principal,
            text=(
                "□ blanco | 1 unidad | # separador | X marca procesada | "
                "0 resultado cero | C2 y C3: la celda 0 guarda el signo | "
                "En la tabla: ? = cualquier símbolo, = = no cambia | "
                "R derecha, L izquierda, S quieto"
            ),
            font=("Arial", 9),
            wraplength=1100,
            justify="left"
        ).grid(row=3, column=0, sticky="ew", pady=(4, 0))

    def crear_panel_cintas(self, panel):
        ttk.Label(
            panel,
            text=(
                "Recorre cada cinta con la barra, la rueda del mouse o "
                "arrastrándola. ⏮ / ⏭ van al inicio / fin del contenido."
            ),
            font=("Arial", 9)
        ).pack(anchor="w", pady=(0, 2))

        self.lienzos = []
        self.etiquetas_cabezal = []
        self.barras = []
        self.contenidos = []

        titulos = ("Cinta 1 (entrada)", "Cinta 2 (trabajo)", "Cinta 3 (salida)")

        for i in range(3):
            marco = ttk.LabelFrame(panel, text=titulos[i], padding=4)
            marco.pack(fill="x", pady=3)
            marco.columnconfigure(0, weight=1)

            lienzo = tk.Canvas(
                marco,
                height=62,
                background="white",
                highlightthickness=1,
                highlightbackground="#999999",
                cursor="fleur"
            )
            lienzo.grid(row=0, column=0, sticky="ew")

            etiqueta = ttk.Label(marco, text="Cabezal: 0", width=12)
            etiqueta.grid(row=0, column=1, padx=6)

            barra = ttk.Scrollbar(
                marco,
                orient="horizontal",
                command=lambda *args, i=i: self.desplazar_cinta(i, *args)
            )
            barra.grid(row=1, column=0, sticky="ew")

            botones = ttk.Frame(marco)
            botones.grid(row=1, column=1)
            ttk.Button(
                botones, text="⏮", width=3,
                command=lambda i=i: self.ir_a(i, "inicio")
            ).pack(side="left")
            ttk.Button(
                botones, text="⏭", width=3,
                command=lambda i=i: self.ir_a(i, "fin")
            ).pack(side="left")

            texto = tk.StringVar()
            ttk.Entry(
                marco, textvariable=texto, state="readonly",
                font=("Consolas", 10)
            ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(3, 0))

            self.lienzos.append(lienzo)
            self.etiquetas_cabezal.append(etiqueta)
            self.barras.append(barra)
            self.contenidos.append(texto)

            lienzo.bind("<Configure>", lambda evento: self.dibujar_cintas())
            lienzo.bind(
                "<MouseWheel>",
                lambda e, i=i: self.rueda(i, -1 if e.delta > 0 else 1)
            )
            lienzo.bind("<Button-4>", lambda e, i=i: self.rueda(i, -1))
            lienzo.bind("<Button-5>", lambda e, i=i: self.rueda(i, 1))
            lienzo.bind(
                "<ButtonPress-1>",
                lambda e, i=i: self.iniciar_arrastre(i, e.x)
            )
            lienzo.bind(
                "<B1-Motion>", lambda e, i=i: self.arrastrar(i, e.x)
            )

    def crear_panel_reglas(self, panel):
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)

        columnas = (
            "numero", "estado", "lee", "escribe",
            "movimientos", "siguiente", "descripcion"
        )

        self.tabla_reglas = ttk.Treeview(
            panel,
            columns=columnas,
            show="headings"
        )

        encabezados = {
            "numero": "N°",
            "estado": "Estado",
            "lee": "Lee C1/C2/C3",
            "escribe": "Escribe C1/C2/C3",
            "movimientos": "Mueve",
            "siguiente": "Siguiente",
            "descripcion": "Qué hace"
        }

        anchos = {
            "numero": 40,
            "estado": 70,
            "lee": 100,
            "escribe": 110,
            "movimientos": 90,
            "siguiente": 80,
            "descripcion": 380
        }

        for columna in columnas:
            self.tabla_reglas.heading(columna, text=encabezados[columna])
            self.tabla_reglas.column(
                columna,
                width=anchos[columna],
                minwidth=40,
                stretch=(columna == "descripcion"),
                anchor="w" if columna == "descripcion" else "center"
            )

        scroll_y = ttk.Scrollbar(
            panel, orient="vertical", command=self.tabla_reglas.yview
        )
        scroll_x = ttk.Scrollbar(
            panel, orient="horizontal", command=self.tabla_reglas.xview
        )

        self.tabla_reglas.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        self.tabla_reglas.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.tabla_reglas.tag_configure("actual", background="#bfdbfe")

    def crear_panel_historial(self, panel):
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)

        self.historial = tk.Text(
            panel,
            font=("Consolas", 10),
            wrap="none",
            state="disabled"
        )

        scroll_y = ttk.Scrollbar(
            panel, orient="vertical", command=self.historial.yview
        )
        scroll_x = ttk.Scrollbar(
            panel, orient="horizontal", command=self.historial.xview
        )

        self.historial.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        self.historial.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        botones = ttk.Frame(panel)
        botones.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Button(
            botones,
            text="Limpiar historial",
            command=self.limpiar_historial
        ).pack(side="left")

    def registrar(self, mensaje):
        self.historial.configure(state="normal")
        self.historial.insert("end", mensaje + "\n")

        lineas = int(self.historial.index("end-1c").split(".")[0])
        if lineas > 5000:
            self.historial.delete("1.0", "1001.0")

        self.historial.see("end")
        self.historial.configure(state="disabled")

    def limpiar_historial(self):
        self.historial.configure(state="normal")
        self.historial.delete("1.0", "end")
        self.historial.configure(state="disabled")

    def registrar_paso(self, p):
        r = p.regla
        self.registrar(
            f"{p.numero:>5}. {p.antes:<5} lee {'/'.join(p.lecturas)}"
            f"  ->  escribe {'/'.join(r.escribe)}  mueve {'/'.join(r.mueve)}"
            f"  ->  {r.siguiente:<8} {r.descripcion}"
        )

    def preparar(self):
        self.pausar()

        try:
            a = leer_entero(self.a.get())
            b = leer_entero(self.b.get())
            op = self.operacion.get()

            if op == "/" and b == 0:
                raise ValueError("No se puede dividir entre cero.")

            if abs(a) > LIMITE_NUMERO or abs(b) > LIMITE_NUMERO:
                raise ValueError(
                    f"Usa numeros entre -{LIMITE_NUMERO} y {LIMITE_NUMERO} "
                    "(en unario la cinta crece muy rapido)."
                )

        except ValueError as error:
            messagebox.showerror("Entrada incorrecta", str(error))
            return

        self.reiniciar()

        self.numero_a = a
        self.numero_b = b
        self.op = op

        entrada = entrada_unaria(a, op, b)
        self.maq = Maquina(op, entrada)
        self.cintas = self.maq.cintas

        total = contar_pasos(op, entrada)
        self.total_texto = str(total) if total is not None else f">{LIMITE_CONTEO}"

        self.resultado_label.config(text="Resultado: pendiente")

        self.registrar("=== MAQUINA PREPARADA ===")
        self.registrar(f"Entrada: {a} {op} {b}")
        self.registrar(f"Cinta 1: {entrada}")
        self.registrar("Cinta 2: espacio de trabajo")
        self.registrar("Cinta 3: salida")
        self.registrar(f"Reglas en la tabla: {len(self.maq.reglas)}")
        self.registrar(f"Pasos que va a tardar: {self.total_texto}")
        self.registrar("")

        self.cargar_reglas_transicion()
        self.refrescar()

        self.pestanas.select(0)

    def cargar_reglas_transicion(self):
        for elemento in self.tabla_reglas.get_children():
            self.tabla_reglas.delete(elemento)

        for i, r in enumerate(self.maq.reglas):
            self.tabla_reglas.insert(
                "",
                "end",
                iid=str(i),
                values=(
                    i + 1,
                    r.estado,
                    " / ".join(r.lee),
                    " / ".join(r.escribe),
                    " / ".join(r.mueve),
                    r.siguiente,
                    r.descripcion
                )
            )

        self.regla_resaltada = None

    def resaltar_regla_actual(self):
        if self.regla_resaltada is not None:
            if self.tabla_reglas.exists(self.regla_resaltada):
                self.tabla_reglas.item(self.regla_resaltada, tags=())

        if self.ultima_regla is None:
            return

        iid = str(self.ultima_regla)
        if self.tabla_reglas.exists(iid):
            self.tabla_reglas.item(iid, tags=("actual",))
            self.tabla_reglas.selection_set(iid)
            self.tabla_reglas.focus(iid)
            self.tabla_reglas.see(iid)
            self.regla_resaltada = iid

    def demora(self):
        v = int(self.velocidad.get())
        return int(1200 * (100 - v) / 100) + 10

    def iniciar(self):
        if self.maq is None:
            messagebox.showinfo("Informacion", "Pulsa Preparar primero.")
            return

        if self.maq.terminada or self.ejecutando:
            return

        self.ejecutando = True
        self.pestanas.select(0)
        self.ejecutar_automatico()

    def ejecutar_automatico(self):
        if not self.ejecutando:
            return

        self.ejecutar_un_paso()

        if self.ejecutando and not self.maq.terminada:
            self.after_id = self.ventana.after(
                self.demora(), self.ejecutar_automatico
            )
        else:
            self.ejecutando = False
            self.after_id = None

    def paso(self):
        self.pausar()

        if self.maq is None:
            messagebox.showinfo("Informacion", "Pulsa Preparar primero.")
            return

        self.ejecutar_un_paso()

    def ejecutar_un_paso(self):
        if self.maq is None or self.maq.terminada:
            return

        p = self.maq.paso()

        if p is not None:
            self.ultima_regla = p.indice
            self.registrar_paso(p)

        self.refrescar()

        if self.maq.terminada:
            self.finalizar()

    def terminar(self):
        if self.maq is None:
            messagebox.showinfo("Informacion", "Pulsa Preparar primero.")
            return

        if self.maq.terminada:
            return

        self.pausar()
        self.ejecutando = True
        self.pestanas.select(0)
        self.registrar("(Ejecucion rapida: no se anota cada paso)")
        self.ejecutar_rapido()

    def ejecutar_rapido(self):
        if not self.ejecutando:
            return

        for _ in range(2000):
            p = self.maq.paso()
            if p is not None:
                self.ultima_regla = p.indice
            if self.maq.terminada or self.maq.pasos >= LIMITE_PASOS:
                break

        self.refrescar()

        if self.maq.terminada:
            self.finalizar()
        elif self.maq.pasos >= LIMITE_PASOS:
            self.pausar()
            messagebox.showwarning(
                "Demasiados pasos",
                f"Se detuvo tras {LIMITE_PASOS} pasos."
            )
        else:
            self.after_id = self.ventana.after(1, self.ejecutar_rapido)

    def finalizar(self):
        if self.resultado_finalizado:
            return

        self.resultado_finalizado = True
        self.pausar()

        m = self.maq
        a, b, op = self.numero_a, self.numero_b, self.op

        self.registrar("")
        self.registrar("=== EJECUCION FINALIZADA ===")
        self.registrar(f"Estado final: {m.estado}")
        self.registrar(f"Pasos: {m.pasos}")

        if m.aceptada:
            valor, residuo = m.resultado()
            if op == "/":
                texto = f"Cociente = {valor}, residuo = {residuo}"
            else:
                texto = str(valor)

            ok = (valor, residuo) == calcular(a, b, op)
            marca = "  ✔" if ok else "  ⚠ no coincide con Python"
            self.resultado_label.config(text="Resultado: " + texto + marca)

            self.registrar("Resultado leido de las cintas: " + texto)
            self.registrar("Cinta 3: " + (m.cintas[2].texto() or "(vacia)"))
            if op == "/":
                self.registrar("Cinta 2: " + (m.cintas[1].texto() or "(vacia)"))
        else:
            self.resultado_label.config(text="Rechazada: " + m.motivo)
            self.registrar("Rechazada: " + m.motivo)

        self.registrar("")
        self.refrescar()

    def pausar(self):
        self.ejecutando = False

        if self.after_id is not None:
            try:
                self.ventana.after_cancel(self.after_id)
            except tk.TclError:
                pass

        self.after_id = None

    def reiniciar(self):
        self.pausar()

        self.maq = None
        self.cintas = [Cinta(), Cinta(), Cinta()]
        self.ultima_regla = None
        self.regla_resaltada = None
        self.total_texto = "0"
        self.resultado_finalizado = False
        self.vistas = [0, 0, 0]

        self.resultado_label.config(text="Resultado: —")

        if hasattr(self, "historial"):
            self.limpiar_historial()

        if hasattr(self, "tabla_reglas"):
            for elemento in self.tabla_reglas.get_children():
                self.tabla_reglas.delete(elemento)

        self.actualizar_estado()
        self.dibujar_cintas()

    def refrescar(self):
        self.actualizar_estado()
        self.resaltar_regla_actual()
        self.dibujar_cintas()

    def actualizar_estado(self):
        estado = self.maq.estado if self.maq else "q0"
        pasos = self.maq.pasos if self.maq else 0

        self.estado_label.config(text=f"Estado: {estado}")
        self.pasos_label.config(text=f"Pasos: {pasos}/{self.total_texto}")

    def rueda(self, i, direccion):
        self.seguir.set(False)
        self.vistas[i] += 3 * direccion
        self.dibujar_cintas()

    def iniciar_arrastre(self, i, x):
        self.arrastre = (x, self.vistas[i])

    def arrastrar(self, i, x):
        if self.arrastre is None:
            return

        x0, vista0 = self.arrastre
        self.seguir.set(False)
        self.vistas[i] = vista0 - (x - x0) // CELDA
        self.dibujar_cintas()

    def desplazar_cinta(self, i, *args):
        self.seguir.set(False)

        if args[0] == "moveto":
            bajo, total = self.rangos[i]
            self.vistas[i] = bajo + int(round(float(args[1]) * total))
        elif args[0] == "scroll":
            cantidad = int(args[1])
            if args[2] == "pages":
                cantidad *= max(1, self.cantidades[i] - 1)
            self.vistas[i] += cantidad

        self.dibujar_cintas()

    def ir_a(self, i, donde):
        self.seguir.set(False)
        limites = self.cintas[i].limites()

        if limites is None:
            self.vistas[i] = -2
        elif donde == "inicio":
            self.vistas[i] = limites[0] - 1
        else:
            self.vistas[i] = limites[1] - self.cantidades[i] + 2

        self.dibujar_cintas()

    def dibujar_cintas(self):
        if not self.listo:
            return

        for i in range(3):
            cinta = self.cintas[i]
            lienzo = self.lienzos[i]
            lienzo.delete("all")

            ancho = lienzo.winfo_width()
            if ancho < 100:
                ancho = 500

            cantidad = max(5, min(60, (ancho - 10) // CELDA))
            self.cantidades[i] = cantidad

            if self.seguir.get():
                self.vistas[i] = cinta.cabezal - cantidad // 2

            inicio = self.vistas[i]

            for j in range(cantidad):
                posicion = inicio + j
                x0 = 5 + j * CELDA
                x1 = x0 + CELDA - 3
                y0, y1 = 6, 36

                simbolo = cinta.leer_posicion(posicion)
                es_cabezal = posicion == cinta.cabezal

                lienzo.create_rectangle(
                    x0, y0, x1, y1,
                    fill="#bfdbfe" if es_cabezal else "white",
                    outline="#2563eb" if es_cabezal else "#94a3b8",
                    width=2 if es_cabezal else 1
                )

                lienzo.create_text(
                    (x0 + x1) / 2,
                    (y0 + y1) / 2,
                    text=simbolo,
                    font=("Consolas", 12, "bold")
                )

                lienzo.create_text(
                    (x0 + x1) / 2,
                    48,
                    text=str(posicion),
                    fill="#64748b",
                    font=("Consolas", 8)
                )

            limites = cinta.limites()
            bajo = min(0, cinta.cabezal, limites[0] if limites else 0) - 2
            alto = max(0, cinta.cabezal, limites[1] if limites else 0) + 3
            bajo = min(bajo, inicio)
            alto = max(alto, inicio + cantidad)
            total = alto - bajo

            self.rangos[i] = (bajo, total)
            self.barras[i].set(
                (inicio - bajo) / total,
                (inicio + cantidad - bajo) / total
            )

            texto = cinta.texto()
            if len(texto) > 3000:
                texto = texto[:3000] + f"… (+{len(texto) - 3000} celdas mas)"
            self.contenidos[i].set(texto if texto else "(vacia)")

            self.etiquetas_cabezal[i].config(text=f"Cabezal: {cinta.cabezal}")

    def cerrar(self):
        self.pausar()
        self.ventana.destroy()


def main():
    if tk is None:
        raise SystemExit("Este programa necesita tkinter instalado.")

    ventana = tk.Tk()
    MaquinaTuring(ventana)
    ventana.mainloop()


if __name__ == "__main__":
    main()