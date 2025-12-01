import re
from typing import List, Union
from app.models.regex import RegexRule
from app.models.preset_regex import PresetRegexRule

class RegexService:
    def process(self, text: str, rules: List[Union[RegexRule, PresetRegexRule]]) -> str:
        for rule in rules:
            if not rule.is_active:
                continue
            try:
                # Support $1, $2 backreferences
                text = re.sub(rule.pattern, rule.replacement, text)
            except re.error:
                # Log error or ignore invalid regex
                pass
        return text

regex_service = RegexService()
