import copy
from typing import Any, Dict, List, Literal, Optional, Set, TypedDict
from dataclasses import dataclass, field
from scripts.generator.lexer import GameType
from scripts.generator.node_transformer import (
    NodeTransformer,
    TransformedComparison,
    TransformedConstant,
    TransformedDate,
    TransformedString,
)
from scripts.generator.parser_manager import ParserManager, ParserManagerConfig


class TechFolderPosition(TypedDict):
    x: int | float | TransformedConstant
    y: int | float | TransformedConstant


class TechFolder(TypedDict):
    name: str
    position: TechFolderPosition


class TechAIWillDoModifier(TypedDict):
    factor: int | float
    trigger_list: List[Any]


@dataclass
class TechAIWillDo:
    factor: int | float
    modifier_list: List[TechAIWillDoModifier]


class TechPath(TypedDict):
    leads_to_tech: str
    research_cost_coeff: float


@dataclass
class Tech:
    name: str
    generation: int
    parents: List[str] = field(default_factory=list)
    path_list: List[TechPath] = field(default_factory=list)
    folder_list: List[TechFolder] = field(default_factory=list)
    on_research_complete: Dict[str, str | bool] = field(default_factory=dict)
    research_cost: float = 0
    start_year: int = 1950
    category_list: List[str] = field(default_factory=list)
    ai_will_do: List[TechAIWillDo] = field(default_factory=list)
    show_effect_as_desc: bool = False
    allow_branch: List[Any] = field(default_factory=list)
    enable_equipment_list: List[str] = field(default_factory=list)
    enable_subunit_list: List[str] = field(default_factory=list)
    enable_equipment_module_list: List[str] = field(default_factory=list)
    effect_list: List[str] = field(default_factory=list)


class TechGroup:
    def __init__(self):
        self.techs: list[Tech] = []


class TechCollection:
    def __init__(
        self, path_str, game_type: GameType = "hoi4", parser_manager_config: Optional[ParserManagerConfig] = None
    ):
        self.parser_manager = ParserManager(path_str, game_type, config=parser_manager_config)
        self.transformed_tree = self.parser_manager.node_transformer.transformed_tree
        self.raw_technologies: Dict[str, Any] = copy.deepcopy(self.transformed_tree.get("technologies", {}))
        self.techs = self._from_transformed_tree(copy.deepcopy(self.raw_technologies))
        self.tech_groups = self._group_techs()

    def _from_transformed_tree(self, technologies_tree: Optional[Dict[str, Any]] = None):
        if technologies_tree is None:
            if "technologies" not in self.transformed_tree:
                raise ValueError("No technologies found in the parsed tree")
            technologies_tree = copy.deepcopy(self.transformed_tree["technologies"])
        if not technologies_tree:
            raise ValueError("No technologies found in the parsed tree")
        _constants = []
        if "_constants" in technologies_tree:
            _constants = technologies_tree.pop("_constants")
        techs: Dict[str, Tech] = {}
        for name, tech in technologies_tree.items():
            # print(name, tech)
            new_tech = Tech(
                name=name,
                generation=0,  # set to 0 for now
                parents=[],  # set to empty list for now
                path_list=self._extract_path_list(tech.pop("path", [])),
                folder_list=self._extract_folder_list(tech.pop("folder", [])),
                on_research_complete=tech.pop("on_research_complete", {}),
                research_cost=tech.pop("research_cost", 0),
                start_year=tech.pop("start_year", 1950),
                category_list=tech.pop("categories", []),
                ai_will_do=self._extract_ai_will_do(tech.pop("ai_will_do", {})),
                show_effect_as_desc=tech.pop("show_effect_as_desc", False),
                allow_branch=[effect for effect in tech.pop("allow_branch", [])],
                enable_equipment_list=[equipment for equipment in tech.pop("enable_equipments", [])],
                enable_subunit_list=[subunit for subunit in tech.pop("enable_subunits", [])],
                enable_equipment_module_list=[module for module in tech.pop("enable_equipment_modules", [])],
                effect_list=[{k: v} for k, v in tech.items()],  # type: ignore too tired to deal with typing anymore fuck me hard in the ass nice and slow
            )
            techs[name] = new_tech

        # determine parents
        for tech in techs.values():
            for path in tech.path_list:
                if path["leads_to_tech"] in techs:
                    techs[path["leads_to_tech"]].parents.append(tech.name)

        def _assign_generation(tech: Tech, generation: int, is_root: bool = False):
            if tech.generation < generation or is_root:
                tech.generation = generation
                for path in tech.path_list:
                    _assign_generation(techs[path["leads_to_tech"]], generation + 1)

        for tech in techs.values():
            if not tech.parents or len(tech.parents) == 0:
                _assign_generation(tech, 0, True)

        return techs

    def _extract_path_list(self, path_list: TechPath | List[TechPath]) -> List[TechPath]:
        if not isinstance(path_list, list):
            return [path_list]
        return path_list

    def _extract_folder_list(self, folder_list: TechFolder | List[TechFolder]) -> List[TechFolder]:
        if not isinstance(folder_list, list):
            folder_list = [folder_list]
            return folder_list
        return folder_list

    def _extract_ai_will_do(self, ai_will_do: Dict[str, Any]) -> List[TechAIWillDo]:
        # modifiers = [
        #     TechAIWillDoModifier(
        #         factor=modifier.pop("factor", 1), trigger_list=[{k: v} for k, v in modifier.items()]
        #     )
        #     for modifier in ai_will_do.get("modifier", [])
        # ]
        # return [TechAIWillDo(factor=ai_will_do.get("factor", 1), modifier_list=modifiers)]
        # print(ai_will_do)
        tech_ai_will_do: list[TechAIWillDo] = []
        for modifier in ai_will_do.get("modifier", []):
            try:
                mod = TechAIWillDoModifier(
                    factor=modifier.pop("factor", 1) if isinstance(modifier, dict) else 0,
                    trigger_list=[{k: v} for k, v in modifier.items() if isinstance(modifier, dict)],
                )
                tech_ai_will_do.append(TechAIWillDo(factor=ai_will_do.get("factor", 1), modifier_list=[mod]))
            except Exception as e:
                print(f"Error extracting AI will do: {e}")
                import json

                # print(f"ai_will_do: {type(ai_will_do)}" + json.dumps(str(ai_will_do)))
                print(f"ai will do (modifier.factor): {type(modifier)} {modifier}")
                print(ai_will_do["modifier"]["factor"])
                # print(modifier.pop())
                # print(f"modifier: {type(modifier)}" + json.dumps(str(modifier)))

        return tech_ai_will_do

    def _group_techs(self, min_generation: int = 1):
        tech_groups: Dict[str, TechGroup] = {}
        for tech in self.techs.values():
            if tech.generation in {0, 1}:  # this will probably duplicate things
                tech_group = TechGroup()
                tech_groups[tech.name] = tech_group
        for name, tech_group in tech_groups.items():
            # for all that have name as parent, add to tech_group
            for tech in self.techs.values():
                try:
                    if name in tech.parents:
                        tech_group.techs.append(tech)
                except Exception as e:
                    print(f"Error grouping techs: {type(tech)} {tech}")


if __name__ == "__main__":
    tech_group = TechCollection(
        "MTG_naval.txt",
        parser_manager_config={"lexer_config": {"enable_logger": False}, "parser_config": {"enable_logger": False}},
    )
    from pprint import pprint

    pprint(tech_group.techs)
