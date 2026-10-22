import itertools
import unittest

from simulador import (
    ACEPTA, BLANCO, CUALQUIERA, IGUAL, RECHAZA,
    Cinta, Maquina, calcular, construir_tabla, contar_pasos,
    entrada_unaria, leer_entero, valor_de_cinta,
)

OPERACIONES = ("+", "-", "*", "/")


def correr(a, op, b, limite=3_000_000):
    m = Maquina(op, entrada_unaria(a, op, b))
    assert m.ejecutar(limite), "no termino"
    return m


class PruebasUtilidades(unittest.TestCase):
    def test_leer_entero(self):
        self.assertEqual(leer_entero(" -12 "), -12)
        self.assertEqual(leer_entero("7"), 7)
        for malo in ("", "-", "1.5", "a", "--1", "1-"):
            with self.assertRaises(ValueError):
                leer_entero(malo)

    def test_calcular_trunca_hacia_cero(self):
        self.assertEqual(calcular(-7, 2, "/"), (-3, -1))
        self.assertEqual(calcular(7, -2, "/"), (-3, 1))
        self.assertEqual(calcular(7, 2, "/"), (3, 1))

    def test_entrada_unaria(self):
        self.assertEqual(entrada_unaria(3, "+", -2), "111#+#-11")
        self.assertEqual(entrada_unaria(0, "-", 0), "#-#")

    def test_cinta(self):
        c = Cinta()
        c.cargar("11")
        c.mover("R")
        c.escribir("X")
        self.assertEqual(c.texto(), "1X")
        c.escribir(BLANCO)
        self.assertEqual(c.celdas, {0: "1"})
        c.mover("L")
        c.mover("L")
        self.assertEqual(c.cabezal, -1)
        with self.assertRaises(ValueError):
            c.mover("Z")


class PruebasTablas(unittest.TestCase):
    def test_estados_definidos_y_sin_ambiguedad(self):
        for op in OPERACIONES:
            reglas = construir_tabla(op)
            origenes = {r.estado for r in reglas}
            self.assertIn("q0", origenes)
            for r in reglas:
                self.assertIn(r.siguiente, origenes | {ACEPTA, RECHAZA})
                self.assertTrue(all(m in "LRS" for m in r.mueve))
                self.assertNotIn(r.estado, (ACEPTA, RECHAZA))

            for e in origenes:
                propias = [r for r in reglas if r.estado == e]
                for r1, r2 in itertools.combinations(propias, 2):
                    solapan = all(
                        p == q or CUALQUIERA in (p, q)
                        for p, q in zip(r1.lee, r2.lee)
                    )
                    if not solapan:
                        continue
                    r1_mas = all(q == CUALQUIERA or p == q
                                 for p, q in zip(r1.lee, r2.lee))
                    r2_mas = all(p == CUALQUIERA or p == q
                                 for p, q in zip(r1.lee, r2.lee))
                    self.assertTrue(
                        (r1_mas or r2_mas) and r1.lee != r2.lee,
                        f"{op}: reglas ambiguas en {e}: {r1.lee} / {r2.lee}",
                    )

    def test_la_tabla_no_depende_de_los_numeros(self):
        m1 = Maquina("+", entrada_unaria(1, "+", 1))
        m2 = Maquina("+", entrada_unaria(400, "+", -250))
        self.assertEqual(m1.reglas, m2.reglas)

    def test_cada_regla_se_usa_alguna_vez(self):
        for op in OPERACIONES:
            usadas = set()
            for a in range(-4, 5):
                for b in range(-4, 5):
                    m = Maquina(op, entrada_unaria(a, op, b))
                    while not m.terminada:
                        p = m.paso()
                        if p:
                            usadas.add(p.indice)
            sobran = set(range(len(construir_tabla(op)))) - usadas
            self.assertEqual(sobran, set(), f"reglas sin usar en '{op}'")


class PruebasAritmetica(unittest.TestCase):
    def test_exhaustivo_pequenos(self):
        for op in OPERACIONES:
            for a in range(-9, 10):
                for b in range(-9, 10):
                    if op == "/" and b == 0:
                        continue
                    m = correr(a, op, b)
                    self.assertTrue(m.aceptada, (a, op, b))
                    self.assertEqual(m.resultado(), calcular(a, b, op), (a, op, b))

    def test_numeros_grandes(self):
        casos = [
            (123, "+", 456), (-300, "+", 299), (500, "-", 499),
            (-500, "-", 500), (99, "*", -98), (-37, "*", -41),
            (500, "/", 7), (-499, "/", 13), (3, "/", 500), (250, "/", 250),
        ]
        for a, op, b in casos:
            m = correr(a, op, b)
            self.assertEqual(m.resultado(), calcular(a, b, op), (a, op, b))

    def test_division_entre_cero_se_rechaza(self):
        for a in (-3, 0, 5):
            m = correr(a, "/", 0)
            self.assertTrue(m.terminada)
            self.assertFalse(m.aceptada)
            self.assertEqual(m.estado, RECHAZA)

    def test_formato_de_las_cintas(self):
        self.assertEqual(correr(7, "+", 3).cintas[2].texto(), "+" + "1" * 10)
        self.assertEqual(correr(3, "-", 7).cintas[2].texto(), "-1111")
        self.assertEqual(correr(5, "-", 5).cintas[2].texto(), "0")
        self.assertEqual(correr(0, "*", -4).cintas[2].texto(), "0")
        m = correr(-7, "/", 2)
        self.assertEqual(m.cintas[2].texto(), "-111")
        self.assertEqual(m.cintas[1].texto(), "-1" )

    def test_valor_de_cinta(self):
        c = Cinta()
        c.cargar("+11")
        self.assertEqual(valor_de_cinta(c), 2)
        c.cargar("-1")
        self.assertEqual(valor_de_cinta(c), -1)
        c.cargar("0")
        self.assertEqual(valor_de_cinta(c), 0)
        c.cargar("11")
        self.assertIsNone(valor_de_cinta(c))


class PruebasMotor(unittest.TestCase):
    def test_sin_regla_rechaza(self):
        m = Maquina("+", "xyz")
        m.ejecutar(100)
        self.assertTrue(m.terminada)
        self.assertFalse(m.aceptada)
        self.assertIn("No hay regla", m.motivo)

    def test_contar_pasos(self):
        total = contar_pasos("+", entrada_unaria(7, "+", 3))
        m = correr(7, "+", 3)
        self.assertEqual(total, m.pasos)
        self.assertIsNone(contar_pasos("*", entrada_unaria(100, "*", 100), limite=50))

    def test_paso_a_paso_igual_que_ejecutar(self):
        m1 = Maquina("*", entrada_unaria(4, "*", -3))
        pasos = 0
        while not m1.terminada:
            self.assertIsNotNone(m1.paso())
            pasos += 1
        m2 = correr(4, "*", -3)
        self.assertEqual(pasos, m2.pasos)
        self.assertEqual(m1.cintas[2].texto(), m2.cintas[2].texto())


if __name__ == "__main__":
    unittest.main()