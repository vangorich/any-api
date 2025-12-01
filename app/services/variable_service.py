import re
import random

class VariableService:
    def __init__(self):
        self.local_vars = {}

    def parse_variables(self, text: str) -> str:
        # 1. Comments {{#...}}
        text = re.sub(r"{{#.*?}}", "", text)

        # 2. Roll {{roll XdY}}
        def roll_repl(match):
            try:
                count, sides = map(int, match.group(1).lower().split('d'))
                total = sum(random.randint(1, sides) for _ in range(count))
                return str(total)
            except:
                return match.group(0)
        text = re.sub(r"{{roll\s+(\d+d\d+)}}", roll_repl, text, flags=re.IGNORECASE)

        # 3. Random {{random::A::B::C}}
        def random_repl(match):
            options = match.group(1).split("::")
            return random.choice(options)
        text = re.sub(r"{{random::(.*?)}}", random_repl, text)

        # 4. Set Var {{setvar::name::value}}
        def setvar_repl(match):
            name = match.group(1)
            value = match.group(2)
            self.local_vars[name] = value
            return ""
        text = re.sub(r"{{setvar::(.*?)::(.*?)}}", setvar_repl, text)

        # 5. Get Var {{getvar::name}}
        def getvar_repl(match):
            name = match.group(1)
            return self.local_vars.get(name, "")
        text = re.sub(r"{{getvar::(.*?)}}", getvar_repl, text)

        return text

variable_service = VariableService()
