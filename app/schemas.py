from pydantic import BaseModel, Field
from typing import Annotated, Optional, List

class AwakenedPower(BaseModel):
    character_name: str
    new_power: str

class ArtifactEvent(BaseModel):
    type: str = Field(description="'create' or 'steal'")
    artifact_name: str
    owner_name: str
    description: str

class RelationshipUpdate(BaseModel):
    type: str
    reason: str

class WarDeclaration(BaseModel):
    aggressor_faction: str
    defender_faction: str
    reason: str

class EncounterResult(BaseModel):
    encounter_idx: int
    p1_name: str
    p2_name: str
    location: str
    dialogue: str
    consequence: str
    is_drama: int
    character_killed: Optional[str] = None
    power_awakened: Optional[AwakenedPower] = None
    artifact_event: Optional[ArtifactEvent] = None
    relationship_update: Optional[RelationshipUpdate] = None
    war_declaration: Optional[WarDeclaration] = None
    p1_snapshot_prompt: Optional[str] = Field(None, description="Stable Diffusion prompt focusing ONLY on p1's PORTRAIT/Expression. NO complex actions, NO holding weapons. e.g. '1boy, angry face, portrait, wearing armor'")
    p2_snapshot_prompt: Optional[str] = Field(None, description="Stable Diffusion prompt focusing ONLY on p2's PORTRAIT/Expression. NO complex actions, NO holding weapons. e.g. '1girl, crying, portrait, looking away'")

class SimulationBatchResult(BaseModel):
    encounters: List[EncounterResult]

class ChapterResult(BaseModel):
    title: str
    body: str
    tone: str


class ChapterPlan(BaseModel):
    source_rounds: List[int]
    pov_characters: List[str]
    central_conflict: str
    political_stake: str
    choice: str
    cost: str
    unresolved_thread: str
    tone: str


class ChapterCritique(BaseModel):
    approved: bool
    blocking_issues: List[str]
    rewrite_brief: str

StatValue = Annotated[int, Field(ge=1, le=100)]


class CharacterSpawnResult(BaseModel):
    name: str
    faction: str
    personality: str
    special_power: str
    gender: str
    sexuality: str
    str: StatValue
    int: StatValue
    cha: StatValue
    agi: StatValue
    race: str
    age: str
    height: str
    weight: str
    skin_color: str
    skills: str
    weapon: str
    class_wealth: str
    morality: str
    ambition: str
    flaw: str
    title: str
    relationship_target: Optional[str] = None
    relationship_type: Optional[str] = None
    image_prompt: str = Field(description="Stable Diffusion prompt focusing ONLY on PORTRAIT/Upper body. NO weapons or action. e.g. '1boy, confident smile, portrait, wearing royal clothes, cinematic'")
