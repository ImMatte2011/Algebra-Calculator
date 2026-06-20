from math_engine import parser, solver

def solve_expression(expr_str: str, type_requested: str, action_requested: str = None, valore_x=None) -> str:
    # 1. Chiama il tuo parser
    parsed = parser.parse_input(expr_str, type_requested, action_requested)
    if "error" in parsed:
        return f"error:{parsed['error']}"

    # 2. Inietta valore_x se presente (in questo modo separiamo il parsing puro dalle variabili extra)
    if valore_x is not None:
        parsed["valore_x"] = valore_x

    # 3. Passa il dizionario al tuo solver
    result = solver.risolvi(parsed)
    if "error" in result:
        return f"error:{result['error']}"

    # 4. Estrazione del dato "sol" e pulizia per l'hardware dell'ESP32
    soluzione = result.get("sol")
    
    if isinstance(soluzione, dict):
        # Caso tipo "expression" (ha le chiavi "res" ed eventualmente "evaluated")
        output = str(soluzione.get("res", ""))
        if "evaluated" in soluzione:
            output += f"={soluzione['evaluated']}"
    else:
        # Caso equazioni/disequazioni (SymPy restituisce Set, es: FiniteSet(2) o {2})
        # Rimuoviamo la dicitura del tipo di oggetto e le graffe per non sporcare l'LCD
        output = str(soluzione).replace("FiniteSet", "").replace("{", "").replace("}", "")

    return f"result:{output}"