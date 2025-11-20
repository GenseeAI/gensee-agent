from collections import OrderedDict
import jinja2
import jinja2.meta
import os

from typing import Optional
from gensee_agent.utils.configs import BaseConfig, register_configs

_AVAILABLE_PROMPT_SECTIONS = [
    "agent_role",
    "rules",
    "tool_use",
    "objective",
    "context",
]

class PromptManager:
    @register_configs("prompt_manager")
    class Config(BaseConfig):
        template_dir: Optional[str] = None  # Path to the template directory.  None to use default.
        template_suffix: str = ".md.j2"  # Suffix for template files. Default is ".md.j2".

    def __init__(self, config: dict):
        self.config = self.Config.from_dict(config)
        self.template_files = {}

        if self.config.template_dir is not None:
            if not os.path.isdir(self.config.template_dir):
                raise ValueError(f"Template directory {self.config.template_dir} does not exist.")

            for filename in os.listdir(self.config.template_dir):
                if filename.endswith(self.config.template_suffix):
                    filepath = os.path.join(self.config.template_dir, filename)
                    base_name = os.path.splitext(filename)[0]
                    with open(filepath, "r") as f:
                        self.template_files[base_name] = f.read()

        from gensee_agent.prompts.data.generic_template import TEMPLATE as default_template
        self.template = default_template

        self.template_variables = jinja2.meta.find_undeclared_variables(jinja2.Environment().parse(self.template))
        if not self.template_variables.issubset(set(_AVAILABLE_PROMPT_SECTIONS)):
            raise ValueError(f"Template variables {self.template_variables} do not match available prompt sections {_AVAILABLE_PROMPT_SECTIONS}")

        self.sections = OrderedDict()
        for section in _AVAILABLE_PROMPT_SECTIONS:
            if section not in self.template_variables:
                continue
            try:
                if section in self.template_files:
                    section_template = self.template_files[section]
                    self.sections[section] = {
                        "template": section_template,
                        "variables": jinja2.meta.find_undeclared_variables(jinja2.Environment().parse(section_template)),
                    }
                    print(f"Loaded prompt section {section} from custom template with variables {self.sections[section]['variables']}")
                else:
                    section_module = __import__(f"gensee_agent.prompts.data.{section}", fromlist=["TEMPLATE"])
                    self.sections[section] = {
                        "template": section_module.TEMPLATE,
                        "variables": jinja2.meta.find_undeclared_variables(jinja2.Environment().parse(section_module.TEMPLATE)),
                    }
                    print(f"Loaded prompt section {section} from system template with variables {self.sections[section]['variables']}")
            except ImportError:
                raise ImportError(f"Could not import prompt section {section} from gensee_agent.prompts.data.{section}")

    def generate_prompt_system_and_user(self, system_prompt: str, user_prompt: str) -> list:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def generate_system_prompt_from_template(self, **kwargs) -> dict:
        template = jinja2.Template(self.template)
        filled_sections = {}
        for section_name, section_data in self.sections.items():
            if not section_data["variables"].issubset(kwargs.keys()):
                raise ValueError(f"Missing variables for section {section_name}: {section_data['variables'] - kwargs.keys()}")
            rendered_section = jinja2.Template(section_data["template"]).render(**kwargs)
            filled_sections[section_name] = rendered_section
        full_prompt = template.render(**filled_sections)
        return {"role": "system", "content": full_prompt}
