import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
PROMPTS_PATH = os.path.join(DATA_DIR, 'prompts.json')

DEFAULT_PROMPTS: List[Dict[str, Any]] = [
	{
		"id": "sitrep",
		"title": "SITREP (Operational Situation Report)",
		"description": "Concise current situation, friendly/enemy forces, key terrain, actions.",
		"prompt_text": "Provide a SITREP: current situation, friendly forces, enemy forces, key terrain, civil considerations, recent actions, and immediate recommendations. Keep it concise and mission-focused.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst"],
		"created_by": "system",
		"version": 1,
		"is_active": True,
		"created_at": datetime.utcnow().isoformat(),
		"updated_at": datetime.utcnow().isoformat()
	},
	{
		"id": "intel-brief",
		"title": "Intelligence Brief (KDF)",
		"description": "Threats, indicators, confidence, and likely courses of action in Kenya.",
		"prompt_text": "Prepare an intelligence brief for KDF: outline key threats, indicators and warnings, confidence levels, and most-likely/most-dangerous courses of action. Tailor to Kenya’s regions and cross-border dynamics.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst"],
		"created_by": "system",
		"version": 1,
		"is_active": True,
		"created_at": datetime.utcnow().isoformat(),
		"updated_at": datetime.utcnow().isoformat()
	},
	{
		"id": "logistics",
		"title": "Logistics Assessment",
		"description": "Supply status, routes, constraints, and recommendations.",
		"prompt_text": "Assess logistics: supply status, lines of communication, route security, constraints (fuel, maintenance, medical), and prioritized recommendations to sustain operations.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst"],
		"created_by": "system",
		"version": 1,
		"is_active": True,
		"created_at": datetime.utcnow().isoformat(),
		"updated_at": datetime.utcnow().isoformat()
	},
	{
		"id": "after-action",
		"title": "After-Action Review (AAR)",
		"description": "What happened, what went well, what to improve, next steps.",
		"prompt_text": "Draft an AAR: what happened, what went well, what can be improved, lessons learned, and next steps. Provide actionable improvements and risk mitigations.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst"],
		"created_by": "system",
		"version": 1,
		"is_active": True,
		"created_at": datetime.utcnow().isoformat(),
		"updated_at": datetime.utcnow().isoformat()
	},
	{
		"id": "public-comm",
		"title": "Public Communication (English + Swahili)",
		"description": "Clear bilingual statement for public release.",
		"prompt_text": "Compose a brief public statement in English with a Swahili translation. Keep it calm, factual, and reassuring. Avoid operational specifics; emphasize public safety and cooperation.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst"],
		"created_by": "system",
		"version": 1,
		"is_active": True,
		"created_at": datetime.utcnow().isoformat(),
		"updated_at": datetime.utcnow().isoformat()
	}
]


def _ensure_store() -> None:
	os.makedirs(DATA_DIR, exist_ok=True)
	if not os.path.exists(PROMPTS_PATH):
		with open(PROMPTS_PATH, 'w', encoding='utf-8') as f:
			json.dump(DEFAULT_PROMPTS, f, ensure_ascii=False, indent=2)


def load_prompts() -> List[Dict[str, Any]]:
	_ensure_store()
	with open(PROMPTS_PATH, 'r', encoding='utf-8') as f:
		return json.load(f)


def save_prompts(prompts: List[Dict[str, Any]]) -> None:
	with open(PROMPTS_PATH, 'w', encoding='utf-8') as f:
		json.dump(prompts, f, ensure_ascii=False, indent=2)


def find_prompt_by_id(pid: str) -> Optional[Dict[str, Any]]:
	for p in load_prompts():
		if p.get('id') == pid and p.get('is_active', True):
			return p
	return None


def filter_prompts_for_role(role: str) -> List[Dict[str, Any]]:
	prompts = load_prompts()
	return [p for p in prompts if p.get('is_active', True) and role in p.get('roles_allowed', [])]


def upsert_prompt(data: Dict[str, Any]) -> Dict[str, Any]:
	prompts = load_prompts()
	existing = None
	for i, p in enumerate(prompts):
		if p.get('id') == data['id']:
			existing = (i, p)
			break
	if existing:
		i, p = existing
		data['version'] = int(p.get('version', 1)) + 1
		data['created_at'] = p.get('created_at')
		data['updated_at'] = datetime.utcnow().isoformat()
		prompts[i] = data
	else:
		data['version'] = int(data.get('version', 1))
		data['created_at'] = data.get('created_at', datetime.utcnow().isoformat())
		data['updated_at'] = datetime.utcnow().isoformat()
		prompts.append(data)
	save_prompts(prompts)
	return data


def soft_delete_prompt(pid: str) -> bool:
	prompts = load_prompts()
	changed = False
	for p in prompts:
		if p.get('id') == pid and p.get('is_active', True):
			p['is_active'] = False
			p['updated_at'] = datetime.utcnow().isoformat()
			changed = True
	if changed:
		save_prompts(prompts)
	return changed
