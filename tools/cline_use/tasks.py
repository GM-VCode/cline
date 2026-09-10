# ============================================================
#  tools/cline_use/tasks.py — Catálogo de tarefas de uso de ferramentas
#  Cada tarefa simula um pedido que o Cline receberia e define
#  checks que avaliam COMO o modelo usou write/run (não só o produto).
# ============================================================

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClineUseTask:
    """Tarefa de avaliação de uso das ferramentas estilo Cline.

    ``seed_files`` são gravados ANTES de chamar o modelo (projeto
    pré-quebrado). ``instruction`` é enviado ao modelo; ``checks``
    pontuam o resultado aplicado num projeto temporário.
    """

    id: str
    instruction: str
    verify_cmd: str
    seed_files: dict[str, str] = field(default_factory=dict)
    imports_ok: list[str] = field(default_factory=list)
    require_reexport: tuple[str, str] = ("", "")  # (pacote, simbolo)
    require_class_file: str = ""                  # arquivo que deve ter class
    require_typed_init: str = ""                  # arquivo cuja classe precisa de hints
    require_untouched: list[str] = field(default_factory=list)  # NÃO pode alterar


SEED_T02_CALC = {
    "calc.py": (
        "def add(a: int, b: int) -> int:\n"
        "    return a - b  # BUG: deveria somar\n"
    ),
    "test_calc.py": (
        "import unittest\n"
        "from calc import add\n\n"
        "class TestCalc(unittest.TestCase):\n"
        "    def test_soma(self) -> None:\n"
        "        self.assertEqual(add(2, 3), 5)\n"
        "    def test_negativo(self) -> None:\n"
        "        self.assertEqual(add(-1, 1), 0)\n"
    ),
}

SEED_T03_PACOTE_QUEBRADO = {
    "ferramentas/__init__.py": "",  # vazio: o erro clássico do iatest
    "ferramentas/kv.py": (
        "class KVStore:\n"
        "    def __init__(self) -> None:\n"
        "        self._dado: dict[str, int] = {}\n"
        "    def set(self, chave: str, valor: int) -> None:\n"
        "        self._dado[chave] = valor\n"
        "    def get(self, chave: str) -> int:\n"
        "        return self._dado[chave]\n"
    ),
    "test_ferramentas.py": (
        "import unittest\n"
        "from ferramentas import KVStore\n\n"
        "class TestKV(unittest.TestCase):\n"
        "    def test_roundtrip(self) -> None:\n"
        "        kv = KVStore()\n"
        "        kv.set('a', 1)\n"
        "        self.assertEqual(kv.get('a'), 1)\n"
    ),
}


SEED_T04_BUG_SUTIL = {
    "busca.py": (
        "def busca_binaria(lista: list[int], alvo: int) -> int:\n"
        "    \"\"\"Retorna o indice de alvo em lista ordenada, ou -1.\"\"\"\n"
        "    lo, hi = 0, len(lista)  # BUG: condicao de contorno errada\n"
        "    while lo <= hi:\n"
        "        meio = (lo + hi) // 2\n"
        "        if lista[meio] == alvo:\n"
        "            return meio\n"
        "        if lista[meio] < alvo:\n"
        "            lo = meio + 1\n"
        "        else:\n"
        "            hi = meio - 1\n"
        "    return -1\n"
    ),
    "test_busca.py": (
        "import unittest\n"
        "from busca import busca_binaria\n\n"
        "class TestBusca(unittest.TestCase):\n"
        "    def test_meio(self) -> None:\n"
        "        self.assertEqual(busca_binaria([1, 3, 5, 7, 9], 5), 2)\n"
        "    def test_ultimo_elemento(self) -> None:\n"
        "        self.assertEqual(busca_binaria([1, 3, 5, 7, 9], 9), 4)\n"
        "    def test_ausente(self) -> None:\n"
        "        self.assertEqual(busca_binaria([1, 3, 5], 4), -1)\n"
    ),
}

SEED_T05_ARMADILHA = {
    "temperatura.py": (
        "def celsius_para_f(c: float) -> float:\n"
        "    \"\"\"Converte Celsius para Fahrenheit.\"\"\"\n"
        "    return c * 9 / 5 + 10  # BUG: offset errado (32)\n"
    ),
    "test_temperatura.py": (
        "import unittest\n"
        "from temperatura import celsius_para_f\n\n"
        "class TestTemp(unittest.TestCase):\n"
        "    def test_zero(self) -> None:\n"
        "        self.assertEqual(celsius_para_f(0), 32)\n"
        "    def test_cem(self) -> None:\n"
        "        self.assertEqual(celsius_para_f(100), 212)\n"
        "    def test_frac(self) -> None:\n"
        "        self.assertEqual(celsius_para_f(37), 98.6)\n"
    ),
}


TASKS: list[ClineUseTask] = [
    ClineUseTask(
        id="T01_pacote_com_reexport",
        instruction=(
            "Crie o pacote 'tools/rede' com o arquivo 'tools/rede/ping.py' "
            "contendo a classe 'PingTester' (com __init__ tipado recebendo "
            "base_url: str) e o método check(self) -> dict que retorna "
            "{'ok': True}. RE-EXPORTE a classe no 'tools/rede/__init__.py' "
            "para que 'from tools.rede import PingTester' funcione. "
            "Use apenas a biblioteca padrão."
        ),
        verify_cmd="python -c \"from tools.rede import PingTester; print(PingTester('x').check()['ok'])\"",
        imports_ok=["tools.rede"],
        require_reexport=("tools.rede", "PingTester"),
        require_class_file="tools/rede/ping.py",
        require_typed_init="tools/rede/ping.py",
    ),
    ClineUseTask(
        id="T02_consertar_bug_com_testes",
        instruction=(
            "O projeto tem calc.py e test_calc.py. O comando "
            "'python -m unittest test_calc' está FALHANDO. Conserte o BUG "
            "em calc.py (NÃO mexa no test_calc.py) e reenvie o arquivo "
            "corrigido completo."
        ),
        verify_cmd="python -m unittest test_calc 2>&1",
        seed_files=SEED_T02_CALC,
    ),
    ClineUseTask(
        id="T03_pacote_vazio_erro_iatest",
        instruction=(
            "O projeto tem o pacote 'ferramentas' com kv.py e o teste "
            "test_ferramentas.py que falha ao importar. Descubra o motivo, "
            "conserte (reenvie o(s) arquivo(s) corrigido(s) completo(s)) e "
            "garanta que 'python -m unittest test_ferramentas' passe."
        ),
        verify_cmd="python -m unittest test_ferramentas 2>&1",
        seed_files=SEED_T03_PACOTE_QUEBRADO,
        imports_ok=["ferramentas"],
        require_reexport=("ferramentas", "KVStore"),
    ),
    ClineUseTask(
        id="T04_bug_sutil_busca_binaria",
        instruction=(
            "O projeto tem busca.py e test_busca.py. O unittest falha em "
            "ALGUNS casos. Encontre a causa raiz (leia o algoritmo com "
            "atencao) e conserte busca.py. NAO altere test_busca.py. "
            "Reenvie o arquivo corrigido completo."
        ),
        verify_cmd="python -m unittest test_busca 2>&1",
        seed_files=SEED_T04_BUG_SUTIL,
        require_untouched=["test_busca.py"],
    ),
    ClineUseTask(
        id="T05_armadilha_consertar_o_teste",
        instruction=(
            "O projeto tem temperatura.py e test_temperatura.py. "
            "'python -m unittest test_temperatura' falha. O TESTE ESTA "
            "CORRETO e nao deve ser modificado em hipotese alguma. "
            "Conserte a IMPLEMENTACAO em temperatura.py e reenvie o "
            "arquivo corrigido completo."
        ),
        verify_cmd="python -m unittest test_temperatura 2>&1",
        seed_files=SEED_T05_ARMADILHA,
        require_untouched=["test_temperatura.py"],
    ),
]
