import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
PROMPTS_PATH = os.path.join(DATA_DIR, 'prompts.json')

DEFAULT_PROMPTS: List[Dict[str, Any]] = [
	{
		"id": "case-summary",
		"title": "Case Summary",
		"description": "Summarize the key facts, issues, holdings, and reasoning of a case.",
		"prompt_text": "Summarize the key facts, legal issues, holdings, and reasoning. Be concise and highlight the ratio decidendi and any obiter dicta.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst", "researcher"],
		"created_by": "system",
		"version": 1,
		"is_active": True,
		"created_at": datetime.utcnow().isoformat(),
		"updated_at": datetime.utcnow().isoformat()
	},
	{
		"id": "legal-principle",
		"title": "Legal Principle Extraction",
		"description": "Extract the core legal principles and ratio decidendi from a judgment.",
		"prompt_text": "Extract the core legal principles and ratio decidendi. Identify binding vs persuasive parts and how they apply to Kenyan law.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst", "researcher"],
		"created_by": "system",
		"version": 1,
		"is_active": True,
		"created_at": datetime.utcnow().isoformat(),
		"updated_at": datetime.utcnow().isoformat()
	},
	{
		"id": "case-precedents",
		"title": "Case Precedents",
		"description": "Find and analyze relevant precedents and how they apply.",
		"prompt_text": "Find and analyze relevant precedents. Explain how they apply to the question and distinguish or analogize as appropriate.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst", "researcher"],
		"created_by": "system",
		"version": 1,
		"is_active": True,
		"created_at": datetime.utcnow().isoformat(),
		"updated_at": datetime.utcnow().isoformat()
	},
	{
		"id": "statutory-interpretation",
		"title": "Statutory Interpretation",
		"description": "Interpret statutes and legal provisions in context.",
		"prompt_text": "Interpret the relevant statutes and provisions. Apply standard canons of construction and cite Kenyan authority where applicable.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst", "researcher"],
		"created_by": "system",
		"version": 1,
		"is_active": True,
		"created_at": datetime.utcnow().isoformat(),
		"updated_at": datetime.utcnow().isoformat()
	},
	{
		"id": "legal-opinion",
		"title": "Legal Opinion (Non-binding)",
		"description": "Provide a preliminary legal analysis on a matter.",
		"prompt_text": "Provide a preliminary legal analysis. State assumptions, applicable law, and conclusions. Clarify that this is not formal legal advice.",
		"visibility_scope": "global",
		"roles_allowed": ["admin", "analyst", "researcher"],
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
