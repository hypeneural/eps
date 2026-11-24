"""Generate local candidate only from a previously released project and reviewed machine contract.

Includes independent modal readback, offline simulation PNG/JSON, and local homologation checklist.
Never approves, publishes, or executes CNC hardware.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from epscad.exporters.tap_simulator import parse_tap_modal, render_tap_simulation
from epscad.publishing.site import verified_source
from epscad.publishing.tap_release import tap_candidate

CHECKLIST = """CANDIDATO LOCAL DE HOMOLOGACAO MACH3 (.TAP) — NAO PUBLICAR / NAO CORTAR SEM VALIDACAO
1. Conferir hash SHA-256 do candidate.tap contra approval.json.
2. Conferir no PC da fabrica (Mach3 / CNC_V): instalacao ativa, CNC_V.xml (DwellinMilli, IJMode, NoSpindle, SpinDelayCW), macros m3.m1s/m5.m1s e passos/mm.
3. Inspecionar candidate_simulation.png (origem 0,0, direcao, limites do bloco, entradas/saidas).
4. Executar dry-run supervisionado no Mach3 com aquecimento do fio fisicamente isolado.
5. Realizar primeiro corte supervisionado em EPS de teste e medir dimensoes fisicas.
6. Somente apos aprovacao humana formal, registrar approved=true e tap_approved=true no registro local com todos os hashes.
"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    _, report, names = verified_source(a.source)
    contract = json.loads(a.contract.read_text(encoding="utf-8"))
    data, hashes = tap_candidate(a.source, report, names, contract)
    parsed = parse_tap_modal(data)
    a.output.mkdir(parents=True, exist_ok=False)
    # Candidate is local and not approved for machine use by this tool.
    (a.output / "candidate.tap").write_bytes(data)
    render_tap_simulation(parsed, a.output / "candidate_simulation.png", title=f"Candidato: {a.source.name}")
    sim_summary = {k: v for k, v in parsed.items() if k != "segments"}
    (a.output / "candidate_simulation.json").write_text(json.dumps(sim_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (a.output / "HOMOLOGATION_CHECKLIST.txt").write_text(CHECKLIST, encoding="utf-8")
    (a.output / "approval.json").write_text(
        json.dumps({"approved": False, "tap_approved": False, "tap_contract": contract, **hashes}, indent=2),
        encoding="utf-8",
    )
    print("LOCAL CANDIDATE ONLY; no publication or machine execution")


if __name__ == "__main__":
    main()
