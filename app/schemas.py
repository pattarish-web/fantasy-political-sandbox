from pydantic import BaseModel, Field
from typing import Optional, List

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
    character_resurrected: Optional[str] = None
    power_awakened: Optional[AwakenedPower] = None
    artifact_event: Optional[ArtifactEvent] = None
    relationship_update: Optional[RelationshipUpdate] = None
    war_declaration: Optional[WarDeclaration] = None
    p1_snapshot_prompt: Optional[str] = None
    p2_snapshot_prompt: Optional[str] = None

class SimulationBatchResult(BaseModel):
    encounters: List[EncounterResult]

class ChapterResult(BaseModel):
    title: str
    body: str
    tone: str

class CharacterSpawnResult(BaseModel):
    name: str
    faction: str
    personality: str
    special_power: str
    gender: Optional[str] = None
    sexuality: Optional[str] = None
    str: Optional[int] = None
    int: Optional[int] = None
    cha: Optional[int] = None
    agi: Optional[int] = None
    race: Optional[str] = None
    age: Optional[str] = None
    height: Optional[str] = None
    weight: Optional[str] = None
    skin_color: Optional[str] = None
    skills: Optional[str] = None
    weapon: Optional[str] = None
    class_wealth: Optional[str] = None
    morality: Optional[str] = None
    ambition: Optional[str] = None
    flaw: Optional[str] = None
    title: Optional[str] = None
    relationship_target: Optional[str] = None
    relationship_type: Optional[str] = None
