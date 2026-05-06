# Smarter edits: Enhanced Post-Editing with LLM Error Highlights and Correction Suggestions

This repository contains the data, code, and interface for the paper **"Smarter Edits? Post-editing with Error Highlights and Translation Suggestions"** (EAMT 2026).

## Overview

We investigate whether LLM-derived error highlights and automatic post-editing (APE) suggestions can improve translator productivity, quality, and user experience in post-editing workflows. Eight professional EN→NL translators post-edited machine-translated texts under four conditions, using **SmartPE** — a custom interface that logs granular editing behaviour.

## Contents

- `data/` — Multi-parallel post-editing dataset (news + biomedical, 2 domains, 8 texts × 4 conditions), including MT outputs, human and automatic error annotations, 8 PE versions, and process data (keystrokes, time)
- `analysis/` — Scripts for productivity, quality, and user experience analysis

## Post-editing Conditions

| Condition | Description |
|-----------|-------------|
| `PE` | Regular post-editing (baseline) |
| `H-QE` | PE + word-level error highlights from xCOMET |
| `H-APE` | PE + error highlights derived from xTower APE |
| `S-APE` | PE + APE highlights with correction suggestions |

## Models

- **Translation**: [xTower-Instruct-13B](https://huggingface.co/Unbabel/TowerInstruct-13B-v0.1) (Treviso et al., 2024)
- **Error spans**: xCOMET-XXL (Guerreiro et al., 2024)
- **APE corrections**: xTower-Instruct-13B-v0.1

## Citation

```bibtex
@inproceedings{smartedits2026,
  title     = {Smarter Edits? Post-editing with Error Highlights and Translation Suggestions},
  booktitle = {Proceedings of EAMT 2026},
  year      = {2026}
}
```
