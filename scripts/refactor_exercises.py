#!/usr/bin/env python3
"""
Refactor exercises.json:
  - Add category (compound|accessory), tier (core|secondary|optional), parent
  - Normalize muscle vocabulary to controlled terms
  - Expand equipment to array where multiple types apply
  - Remove duplicate (Dumbbell Clean / Dumbbell Power Clean)
  - Separate aliases (same movement) vs variations (different exercises with parent)
"""
import json
import os

SRC = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'exercises.json')

# ── Controlled muscle vocabulary ──────────────────────────────────────────────
# Allowed primary/secondary values after normalization:
# quads, hamstrings, glutes, calves, chest, lats, mid_back, erectors, traps,
# anterior_delts, lateral_delts, posterior_delts, biceps, triceps, forearms,
# abs, obliques, hip_flexors

MUSCLE_OVERRIDES = {
    # ── Squats ──
    "Back Squat":           {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "hamstrings", "abs"]},
    "Front Squat":          {"primary_muscle": "quads",   "secondary_muscles": ["abs", "glutes"]},
    "Pause Squat":          {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "abs"]},
    "Box Squat":            {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "hamstrings"]},
    "Safety Bar Squat":     {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "abs"]},
    "Overhead Squat":       {"primary_muscle": "quads",   "secondary_muscles": ["anterior_delts", "abs"]},
    "Goblet Squat":         {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "abs"]},
    "Kettlebell Front Squat": {"primary_muscle": "quads", "secondary_muscles": ["abs", "glutes"]},
    "Leg Press":            {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "hamstrings"]},
    "Hack Squat Machine":   {"primary_muscle": "quads",   "secondary_muscles": ["glutes"]},
    "Belt Squat":           {"primary_muscle": "quads",   "secondary_muscles": ["glutes"]},
    "Smith Machine Squat":  {"primary_muscle": "quads",   "secondary_muscles": ["glutes"]},
    "Sumo Squat":           {"primary_muscle": "glutes",  "secondary_muscles": ["quads", "hamstrings"]},
    "Bulgarian Split Squat":{"primary_muscle": "quads",   "secondary_muscles": ["glutes", "hamstrings"]},
    "Dumbbell Split Squat": {"primary_muscle": "quads",   "secondary_muscles": ["glutes"]},
    "Dumbbell Lunge":       {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "hamstrings"]},
    "Barbell Lunge":        {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "hamstrings"]},
    "Dumbbell Step Up":     {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "hamstrings"]},
    "Barbell Step Up":      {"primary_muscle": "quads",   "secondary_muscles": ["glutes"]},
    "Pistol Squat":         {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "abs"]},
    "Jump Squat":           {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "calves"]},
    "Box Jump":             {"primary_muscle": "quads",   "secondary_muscles": ["glutes", "calves"]},
    "Wall Sit":             {"primary_muscle": "quads",   "secondary_muscles": ["glutes"]},
    "Hip Abductor Machine": {"primary_muscle": "glutes",  "secondary_muscles": []},
    "Hip Adductor Machine": {"primary_muscle": "quads",   "secondary_muscles": []},
    "Band Lateral Walk":    {"primary_muscle": "glutes",  "secondary_muscles": []},
    # ── Hinges / Deadlifts ──
    "Conventional Deadlift":   {"primary_muscle": "hamstrings", "secondary_muscles": ["glutes", "erectors", "traps", "abs"]},
    "Sumo Deadlift":           {"primary_muscle": "glutes",     "secondary_muscles": ["hamstrings", "quads", "erectors"]},
    "Romanian Deadlift":       {"primary_muscle": "hamstrings", "secondary_muscles": ["glutes", "erectors"]},
    "Dumbbell Romanian Deadlift":  {"primary_muscle": "hamstrings", "secondary_muscles": ["glutes", "erectors"]},
    "Kettlebell Romanian Deadlift":{"primary_muscle": "hamstrings", "secondary_muscles": ["glutes", "erectors"]},
    "Cable Romanian Deadlift": {"primary_muscle": "hamstrings", "secondary_muscles": ["glutes"]},
    "Single Leg Romanian Deadlift": {"primary_muscle": "hamstrings", "secondary_muscles": ["glutes", "abs"]},
    "Trap Bar Deadlift":       {"primary_muscle": "hamstrings", "secondary_muscles": ["glutes", "quads", "erectors", "traps"]},
    "Deficit Deadlift":        {"primary_muscle": "hamstrings", "secondary_muscles": ["glutes", "erectors"]},
    "Rack Pull":               {"primary_muscle": "erectors",   "secondary_muscles": ["traps", "glutes"]},
    "Barbell Good Morning":    {"primary_muscle": "erectors",   "secondary_muscles": ["hamstrings", "glutes"]},
    "Back Extension":          {"primary_muscle": "erectors",   "secondary_muscles": ["glutes", "hamstrings"]},
    "Reverse Hyper":           {"primary_muscle": "glutes",     "secondary_muscles": ["hamstrings", "erectors"]},
    "Cable Hip Hinge":         {"primary_muscle": "glutes",     "secondary_muscles": ["hamstrings", "erectors"]},
    "Cable Pull-Through":      {"primary_muscle": "glutes",     "secondary_muscles": ["hamstrings"]},
    "Nordic Hamstring Curl":   {"primary_muscle": "hamstrings", "secondary_muscles": []},
    "Glute Ham Raise":         {"primary_muscle": "hamstrings", "secondary_muscles": ["glutes"]},
    "Lying Leg Curl":          {"primary_muscle": "hamstrings", "secondary_muscles": []},
    "Seated Leg Curl":         {"primary_muscle": "hamstrings", "secondary_muscles": []},
    # ── Hip Thrusts / Glute Bridges ──
    "Hip Thrust":                    {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "abs"]},
    "Dumbbell Hip Thrust":           {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings"]},
    "Single Leg Hip Thrust":         {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings"]},
    "Single Leg Hip Thrust (Dumbbell)": {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings"]},
    "Hip Thrust Machine":            {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings"]},
    "Band Hip Thrust":               {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings"]},
    "Glute Bridge":                  {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "abs"]},
    # ── Presses ──
    "Bench Press":           {"primary_muscle": "chest",         "secondary_muscles": ["triceps", "anterior_delts"]},
    "Incline Bench Press":   {"primary_muscle": "chest",         "secondary_muscles": ["triceps", "anterior_delts"]},
    "Decline Bench Press":   {"primary_muscle": "chest",         "secondary_muscles": ["triceps"]},
    "Paused Bench Press":    {"primary_muscle": "chest",         "secondary_muscles": ["triceps", "anterior_delts"]},
    "Close Grip Bench Press":{"primary_muscle": "triceps",       "secondary_muscles": ["chest", "anterior_delts"]},
    "Dumbbell Bench Press":  {"primary_muscle": "chest",         "secondary_muscles": ["triceps", "anterior_delts"]},
    "Incline Dumbbell Press":{"primary_muscle": "chest",         "secondary_muscles": ["triceps", "anterior_delts"]},
    "Decline Dumbbell Press":{"primary_muscle": "chest",         "secondary_muscles": ["triceps"]},
    "Dumbbell Squeeze Press":{"primary_muscle": "chest",         "secondary_muscles": ["triceps"]},
    "Chest Press Machine":   {"primary_muscle": "chest",         "secondary_muscles": ["triceps", "anterior_delts"]},
    "Incline Chest Press Machine": {"primary_muscle": "chest",   "secondary_muscles": ["triceps", "anterior_delts"]},
    "Push-Up":               {"primary_muscle": "chest",         "secondary_muscles": ["triceps", "anterior_delts", "abs"]},
    "Decline Push-Up":       {"primary_muscle": "chest",         "secondary_muscles": ["triceps", "anterior_delts"]},
    "Incline Push-Up":       {"primary_muscle": "chest",         "secondary_muscles": ["triceps"]},
    "Deficit Push-Up":       {"primary_muscle": "chest",         "secondary_muscles": ["triceps", "anterior_delts"]},
    "Dip":                   {"primary_muscle": "triceps",       "secondary_muscles": ["chest", "anterior_delts"]},
    "Ring Dip":              {"primary_muscle": "triceps",       "secondary_muscles": ["chest", "anterior_delts"]},
    "Diamond Push-Up":       {"primary_muscle": "triceps",       "secondary_muscles": ["chest"]},
    "Pike Push-Up":          {"primary_muscle": "anterior_delts","secondary_muscles": ["triceps"]},
    "Overhead Press":        {"primary_muscle": "anterior_delts","secondary_muscles": ["triceps", "abs", "traps", "lateral_delts"]},
    "Dumbbell Shoulder Press":{"primary_muscle": "anterior_delts","secondary_muscles": ["triceps", "lateral_delts"]},
    "Arnold Press":          {"primary_muscle": "anterior_delts","secondary_muscles": ["lateral_delts", "triceps"]},
    "Shoulder Press Machine":{"primary_muscle": "anterior_delts","secondary_muscles": ["triceps", "lateral_delts"]},
    "Kettlebell Press":      {"primary_muscle": "anterior_delts","secondary_muscles": ["triceps", "abs"]},
    "Landmine Press":        {"primary_muscle": "anterior_delts","secondary_muscles": ["triceps", "chest"]},
    "Push Press":            {"primary_muscle": "anterior_delts","secondary_muscles": ["triceps", "quads", "abs"]},
    "Push Jerk":             {"primary_muscle": "anterior_delts","secondary_muscles": ["triceps", "quads", "abs"]},
    "Split Jerk":            {"primary_muscle": "anterior_delts","secondary_muscles": ["triceps", "quads", "abs"]},
    # ── Chest isolation ──
    "Dumbbell Fly":          {"primary_muscle": "chest", "secondary_muscles": []},
    "Incline Dumbbell Fly":  {"primary_muscle": "chest", "secondary_muscles": []},
    "Cable Fly":             {"primary_muscle": "chest", "secondary_muscles": []},
    "Low Cable Fly":         {"primary_muscle": "chest", "secondary_muscles": []},
    "High Cable Fly":        {"primary_muscle": "chest", "secondary_muscles": []},
    "Pec Deck":              {"primary_muscle": "chest", "secondary_muscles": []},
    # ── Pulls / Rows ──
    "Pull-Up":               {"primary_muscle": "lats",     "secondary_muscles": ["biceps", "mid_back"]},
    "Chin-Up":               {"primary_muscle": "lats",     "secondary_muscles": ["biceps", "mid_back"]},
    "Neutral Grip Pull-Up":  {"primary_muscle": "lats",     "secondary_muscles": ["biceps", "mid_back"]},
    "Ring Pull-Up":          {"primary_muscle": "lats",     "secondary_muscles": ["biceps", "mid_back", "abs"]},
    "Assisted Pull-Up":      {"primary_muscle": "lats",     "secondary_muscles": ["biceps"]},
    "Lat Pulldown":          {"primary_muscle": "lats",     "secondary_muscles": ["biceps", "mid_back"]},
    "Close Grip Lat Pulldown":{"primary_muscle": "lats",    "secondary_muscles": ["biceps", "mid_back"]},
    "Single Arm Lat Pulldown":{"primary_muscle": "lats",    "secondary_muscles": ["biceps"]},
    "Straight Arm Pulldown": {"primary_muscle": "lats",     "secondary_muscles": ["abs"]},
    "Bent Over Row":         {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps", "traps"]},
    "Yates Row":             {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps"]},
    "Pendlay Row":           {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps", "traps"]},
    "Single Arm Dumbbell Row":{"primary_muscle": "mid_back","secondary_muscles": ["lats", "biceps", "traps"]},
    "Chest Supported Dumbbell Row":{"primary_muscle": "mid_back","secondary_muscles": ["lats", "biceps", "traps"]},
    "Chest Supported Row Machine": {"primary_muscle": "mid_back","secondary_muscles": ["lats", "biceps"]},
    "Seated Cable Row":      {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps", "traps"]},
    "Standing Cable Row":    {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps", "abs"]},
    "Single Arm Cable Row":  {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps"]},
    "Seated Row Machine":    {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps"]},
    "T-Bar Row":             {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps", "traps"]},
    "Landmine Row":          {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps"]},
    "Inverted Row":          {"primary_muscle": "mid_back", "secondary_muscles": ["lats", "biceps"]},
    "Dumbbell Pullover":     {"primary_muscle": "lats",     "secondary_muscles": ["chest", "triceps"]},
    "Cable Face Pull":       {"primary_muscle": "posterior_delts", "secondary_muscles": ["traps", "mid_back"]},
    "Dumbbell Rear Delt Fly":{"primary_muscle": "posterior_delts", "secondary_muscles": ["traps", "mid_back"]},
    "Cable Rear Delt Fly":   {"primary_muscle": "posterior_delts", "secondary_muscles": ["traps", "mid_back"]},
    "Band Pull Apart":       {"primary_muscle": "posterior_delts", "secondary_muscles": ["traps", "mid_back"]},
    # ── Shoulder isolation ──
    "Dumbbell Lateral Raise":{"primary_muscle": "lateral_delts", "secondary_muscles": []},
    "Cable Lateral Raise":   {"primary_muscle": "lateral_delts", "secondary_muscles": []},
    "Lateral Raise Machine": {"primary_muscle": "lateral_delts", "secondary_muscles": []},
    "Dumbbell Front Raise":  {"primary_muscle": "anterior_delts","secondary_muscles": []},
    "Cable Front Raise":     {"primary_muscle": "anterior_delts","secondary_muscles": []},
    "Dumbbell Upright Row":  {"primary_muscle": "traps",         "secondary_muscles": ["lateral_delts"]},
    "Muscle Snatch":         {"primary_muscle": "anterior_delts","secondary_muscles": ["traps", "mid_back"]},
    # ── Shrugs / Traps ──
    "Dumbbell Shrug":        {"primary_muscle": "traps", "secondary_muscles": []},
    "Barbell Shrug":         {"primary_muscle": "traps", "secondary_muscles": []},
    "Farmer Walk":           {"primary_muscle": "traps", "secondary_muscles": ["forearms", "abs", "quads"]},
    "Suitcase Carry":        {"primary_muscle": "obliques", "secondary_muscles": ["traps", "forearms"]},
    "Turkish Get-Up":        {"primary_muscle": "anterior_delts", "secondary_muscles": ["abs", "glutes"]},
    # ── Core ──
    "Plank":            {"primary_muscle": "abs",      "secondary_muscles": ["anterior_delts"]},
    "Side Plank":       {"primary_muscle": "obliques", "secondary_muscles": ["anterior_delts"]},
    "Ab Wheel Rollout": {"primary_muscle": "abs",      "secondary_muscles": ["lats", "anterior_delts"]},
    "Cable Crunch":     {"primary_muscle": "abs",      "secondary_muscles": []},
    "Hanging Leg Raise":{"primary_muscle": "abs",      "secondary_muscles": ["hip_flexors"]},
    "Russian Twist":    {"primary_muscle": "obliques", "secondary_muscles": []},
    "Hollow Body Hold": {"primary_muscle": "abs",      "secondary_muscles": []},
    "Dead Bug":         {"primary_muscle": "abs",      "secondary_muscles": []},
    "Bird Dog":         {"primary_muscle": "abs",      "secondary_muscles": ["erectors", "glutes"]},
    "Pallof Press":     {"primary_muscle": "obliques", "secondary_muscles": ["anterior_delts"]},
    "Cable Woodchop":   {"primary_muscle": "obliques", "secondary_muscles": ["anterior_delts"]},
    "Toes to Bar":      {"primary_muscle": "abs",      "secondary_muscles": ["hip_flexors"]},
    "Knees to Chest":   {"primary_muscle": "abs",      "secondary_muscles": ["hip_flexors"]},
    # ── Biceps ──
    "Dumbbell Curl":         {"primary_muscle": "biceps", "secondary_muscles": ["forearms"]},
    "Barbell Curl":          {"primary_muscle": "biceps", "secondary_muscles": ["forearms"]},
    "Hammer Curl":           {"primary_muscle": "biceps", "secondary_muscles": ["forearms"]},
    "EZ Bar Curl":           {"primary_muscle": "biceps", "secondary_muscles": ["forearms"]},
    "Preacher Curl":         {"primary_muscle": "biceps", "secondary_muscles": []},
    "Cable Curl":            {"primary_muscle": "biceps", "secondary_muscles": []},
    "Machine Preacher Curl": {"primary_muscle": "biceps", "secondary_muscles": []},
    "Single Arm Cable Curl": {"primary_muscle": "biceps", "secondary_muscles": []},
    "Concentration Curl":    {"primary_muscle": "biceps", "secondary_muscles": []},
    "Incline Dumbbell Curl": {"primary_muscle": "biceps", "secondary_muscles": []},
    "Spider Curl":           {"primary_muscle": "biceps", "secondary_muscles": []},
    "Zottman Curl":          {"primary_muscle": "biceps", "secondary_muscles": ["forearms"]},
    "Drag Curl":             {"primary_muscle": "biceps", "secondary_muscles": []},
    "Cable Hammer Curl":     {"primary_muscle": "biceps", "secondary_muscles": ["forearms"]},
    "Band Bicep Curl":       {"primary_muscle": "biceps", "secondary_muscles": []},
    "Barbell Reverse Curl":  {"primary_muscle": "forearms", "secondary_muscles": ["biceps"]},
    "Reverse Cable Curl":    {"primary_muscle": "forearms", "secondary_muscles": ["biceps"]},
    # ── Triceps ──
    "Tricep Pushdown":               {"primary_muscle": "triceps", "secondary_muscles": []},
    "Tricep Rope Pushdown":          {"primary_muscle": "triceps", "secondary_muscles": []},
    "Barbell Skull Crusher":         {"primary_muscle": "triceps", "secondary_muscles": []},
    "Dumbbell Skull Crusher":        {"primary_muscle": "triceps", "secondary_muscles": []},
    "EZ Bar Skull Crusher":          {"primary_muscle": "triceps", "secondary_muscles": []},
    "Cable Overhead Tricep Extension":   {"primary_muscle": "triceps", "secondary_muscles": []},
    "Dumbbell Overhead Tricep Extension":{"primary_muscle": "triceps", "secondary_muscles": []},
    "Cable Tricep Kickback":         {"primary_muscle": "triceps", "secondary_muscles": []},
    "Dumbbell Tricep Kickback":      {"primary_muscle": "triceps", "secondary_muscles": []},
    "Tricep Dip Machine":            {"primary_muscle": "triceps", "secondary_muscles": ["chest"]},
    "Tricep Extension Machine":      {"primary_muscle": "triceps", "secondary_muscles": []},
    "Band Tricep Pushdown":          {"primary_muscle": "triceps", "secondary_muscles": []},
    # ── Olympic lifts ──
    "Power Clean":    {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "erectors", "traps", "anterior_delts"]},
    "Hang Power Clean":{"primary_muscle": "glutes","secondary_muscles": ["hamstrings", "erectors", "traps", "anterior_delts"]},
    "Clean":          {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "quads", "erectors", "anterior_delts"]},
    "Hang Clean":     {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "quads", "erectors", "anterior_delts"]},
    "Clean and Jerk": {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "quads", "anterior_delts", "triceps"]},
    "Power Snatch":   {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "erectors", "traps", "anterior_delts"]},
    "Hang Power Snatch":{"primary_muscle": "glutes","secondary_muscles": ["hamstrings", "erectors", "traps", "anterior_delts"]},
    "Snatch":         {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "quads", "erectors", "anterior_delts"]},
    "Hang Snatch":    {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "quads", "erectors", "anterior_delts"]},
    "Clean Pull":     {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "traps", "erectors"]},
    "Snatch Pull":    {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "traps", "erectors"]},
    "Dumbbell Clean": {"primary_muscle": "glutes", "secondary_muscles": ["hamstrings", "erectors", "anterior_delts"]},
    "Kettlebell Clean":{"primary_muscle": "glutes","secondary_muscles": ["erectors", "anterior_delts"]},
    "Kettlebell Snatch":{"primary_muscle": "glutes","secondary_muscles": ["anterior_delts", "erectors"]},
    "Kettlebell Clean and Press":{"primary_muscle": "glutes","secondary_muscles": ["anterior_delts", "erectors", "hamstrings"]},
    "Kettlebell Swing":{"primary_muscle": "glutes","secondary_muscles": ["hamstrings", "abs", "erectors"]},
    "Single Arm Kettlebell Swing":{"primary_muscle": "glutes","secondary_muscles": ["hamstrings", "abs"]},
    "Kettlebell Deadlift":{"primary_muscle": "hamstrings","secondary_muscles": ["glutes", "erectors"]},
    # ── Carries / other ──
    "Sled Push": {"primary_muscle": "quads", "secondary_muscles": ["glutes", "abs"]},
}

# ── Category + Tier ──────────────────────────────────────────────────────────
CATEGORY_TIER = {
    # core = foundational movement most athletes should do; secondary = important but not primary;
    # optional = specific, variation, or niche
    "Back Squat":            ("compound", "core"),
    "Bench Press":           ("compound", "core"),
    "Conventional Deadlift": ("compound", "core"),
    "Overhead Press":        ("compound", "core"),
    "Pull-Up":               ("compound", "core"),
    "Bent Over Row":         ("compound", "core"),
    "Romanian Deadlift":     ("compound", "core"),
    "Hip Thrust":            ("compound", "core"),
    "Bulgarian Split Squat": ("compound", "core"),

    "Front Squat":           ("compound", "secondary"),
    "Incline Bench Press":   ("compound", "secondary"),
    "Sumo Deadlift":         ("compound", "secondary"),
    "Trap Bar Deadlift":     ("compound", "secondary"),
    "Chin-Up":               ("compound", "secondary"),
    "Lat Pulldown":          ("compound", "secondary"),
    "Seated Cable Row":      ("compound", "secondary"),
    "Single Arm Dumbbell Row":("compound","secondary"),
    "Dumbbell Bench Press":  ("compound", "secondary"),
    "Dumbbell Shoulder Press":("compound","secondary"),
    "Push-Up":               ("compound", "secondary"),
    "Dip":                   ("compound", "secondary"),
    "Goblet Squat":          ("compound", "secondary"),
    "Leg Press":             ("compound", "secondary"),
    "Dumbbell Romanian Deadlift":("compound","secondary"),
    "Hack Squat Machine":    ("compound", "secondary"),
    "Push Press":            ("compound", "secondary"),
    "Kettlebell Swing":      ("compound", "secondary"),
    "Incline Dumbbell Press":("compound", "secondary"),
    "Dumbbell Lunge":        ("compound", "secondary"),
    "Power Clean":           ("compound", "secondary"),
    "Power Snatch":          ("compound", "secondary"),
    "Clean":                 ("compound", "secondary"),
    "Snatch":                ("compound", "secondary"),
    "Clean and Jerk":        ("compound", "secondary"),
    "Chest Supported Dumbbell Row":("compound","secondary"),
    "Inverted Row":          ("compound", "secondary"),
    "Glute Bridge":          ("compound", "secondary"),
    "Safety Bar Squat":      ("compound", "secondary"),
    "Close Grip Bench Press":("compound", "secondary"),
    "T-Bar Row":             ("compound", "secondary"),
    "Nordic Hamstring Curl": ("compound", "secondary"),
    "Glute Ham Raise":       ("compound", "secondary"),
    "Single Leg Romanian Deadlift":("compound","secondary"),
    "Turkish Get-Up":        ("compound", "secondary"),
    "Barbell Good Morning":  ("compound", "secondary"),
    "Cable Pull-Through":    ("compound", "secondary"),
    "Back Extension":        ("compound", "secondary"),
    "Dumbbell Step Up":      ("compound", "secondary"),
    "Box Jump":              ("compound", "secondary"),
    "Sled Push":             ("compound", "secondary"),
    "Farmer Walk":           ("compound", "secondary"),
    "Suitcase Carry":        ("compound", "secondary"),
    "Cable Face Pull":       ("accessory","secondary"),
    "Dumbbell Lateral Raise":("accessory","secondary"),
    "Dumbbell Curl":         ("accessory","secondary"),
    "Barbell Curl":          ("accessory","secondary"),
    "EZ Bar Curl":           ("accessory","secondary"),
    "Hammer Curl":           ("accessory","secondary"),
    "Tricep Pushdown":       ("accessory","secondary"),
    "Barbell Skull Crusher": ("accessory","secondary"),
    "Dumbbell Rear Delt Fly":("accessory","secondary"),
    "Lying Leg Curl":        ("accessory","secondary"),
    "Leg Extension":         ("accessory","secondary"),
    "Seated Calf Raise":     ("accessory","secondary"),
    "Standing Calf Raise":   ("accessory","secondary"),
    "Dumbbell Shrug":        ("accessory","secondary"),
    "Barbell Shrug":         ("accessory","secondary"),
    "Plank":                 ("accessory","secondary"),
    "Side Plank":            ("accessory","secondary"),
    "Ab Wheel Rollout":      ("accessory","secondary"),
    "Cable Crunch":          ("accessory","secondary"),
    "Hanging Leg Raise":     ("accessory","secondary"),
    "Dead Bug":              ("accessory","secondary"),
    "Bird Dog":              ("accessory","secondary"),
    "Pallof Press":          ("accessory","secondary"),
    "Toes to Bar":           ("accessory","secondary"),
    "Band Pull Apart":       ("accessory","secondary"),
    "Cable Fly":             ("accessory","secondary"),
    "Dumbbell Fly":          ("accessory","secondary"),

    "Pause Squat":           ("compound", "optional"),
    "Box Squat":             ("compound", "optional"),
    "Deficit Deadlift":      ("compound", "optional"),
    "Rack Pull":             ("compound", "optional"),
    "Paused Bench Press":    ("compound", "optional"),
    "Decline Bench Press":   ("compound", "optional"),
    "Overhead Squat":        ("compound", "optional"),
    "Hang Power Clean":      ("compound", "optional"),
    "Hang Clean":            ("compound", "optional"),
    "Hang Power Snatch":     ("compound", "optional"),
    "Hang Snatch":           ("compound", "optional"),
    "Push Jerk":             ("compound", "optional"),
    "Split Jerk":            ("compound", "optional"),
    "Clean Pull":            ("compound", "optional"),
    "Snatch Pull":           ("compound", "optional"),
    "Muscle Snatch":         ("compound", "optional"),
    "Dumbbell Clean":        ("compound", "optional"),
    "Kettlebell Clean and Press":("compound","optional"),
    "Kettlebell Clean":      ("compound", "optional"),
    "Kettlebell Snatch":     ("compound", "optional"),
    "Kettlebell Romanian Deadlift":("compound","optional"),
    "Kettlebell Deadlift":   ("compound", "optional"),
    "Kettlebell Front Squat":("compound", "optional"),
    "Kettlebell Press":      ("compound", "optional"),
    "Single Arm Kettlebell Swing":("compound","optional"),
    "Reverse Hyper":         ("compound", "optional"),
    "Barbell Lunge":         ("compound", "optional"),
    "Barbell Step Up":       ("compound", "optional"),
    "Dumbbell Split Squat":  ("compound", "optional"),
    "Pistol Squat":          ("compound", "optional"),
    "Jump Squat":            ("compound", "optional"),
    "Belt Squat":            ("compound", "optional"),
    "Smith Machine Squat":   ("compound", "optional"),
    "Single Leg Hip Thrust": ("compound", "optional"),
    "Single Leg Hip Thrust (Dumbbell)":("compound","optional"),
    "Dumbbell Hip Thrust":   ("compound", "optional"),
    "Hip Thrust Machine":    ("compound", "optional"),
    "Band Hip Thrust":       ("compound", "optional"),
    "Neutral Grip Pull-Up":  ("compound", "optional"),
    "Ring Pull-Up":          ("compound", "optional"),
    "Ring Dip":              ("compound", "optional"),
    "Assisted Pull-Up":      ("compound", "optional"),
    "Pendlay Row":           ("compound", "optional"),
    "Yates Row":             ("compound", "optional"),
    "Chest Supported Row Machine":("compound","optional"),
    "Seated Row Machine":    ("compound", "optional"),
    "Standing Cable Row":    ("compound", "optional"),
    "Single Arm Cable Row":  ("compound", "optional"),
    "Landmine Press":        ("compound", "optional"),
    "Landmine Row":          ("compound", "optional"),
    "Decline Dumbbell Press":("compound", "optional"),
    "Decline Push-Up":       ("compound", "optional"),
    "Incline Push-Up":       ("compound", "optional"),
    "Deficit Push-Up":       ("compound", "optional"),
    "Incline Chest Press Machine":("compound","optional"),
    "Sumo Squat":            ("compound", "optional"),
    "Cable Hip Hinge":       ("compound", "optional"),
    "Dumbbell Clean":        ("compound", "optional"),
    "Arnold Press":          ("accessory","optional"),
    "Shoulder Press Machine":("accessory","optional"),
    "Tricep Rope Pushdown":  ("accessory","optional"),
    "Dumbbell Skull Crusher":("accessory","optional"),
    "EZ Bar Skull Crusher":  ("accessory","optional"),
    "Cable Overhead Tricep Extension":("accessory","optional"),
    "Dumbbell Overhead Tricep Extension":("accessory","optional"),
    "Diamond Push-Up":       ("accessory","optional"),
    "Pike Push-Up":          ("accessory","optional"),
    "Tricep Dip Machine":    ("accessory","optional"),
    "Tricep Extension Machine":("accessory","optional"),
    "Cable Tricep Kickback": ("accessory","optional"),
    "Dumbbell Tricep Kickback":("accessory","optional"),
    "Band Tricep Pushdown":  ("accessory","optional"),
    "Cable Lateral Raise":   ("accessory","optional"),
    "Lateral Raise Machine": ("accessory","optional"),
    "Dumbbell Front Raise":  ("accessory","optional"),
    "Cable Front Raise":     ("accessory","optional"),
    "Cable Rear Delt Fly":   ("accessory","optional"),
    "Dumbbell Upright Row":  ("accessory","optional"),
    "Preacher Curl":         ("accessory","optional"),
    "Cable Curl":            ("accessory","optional"),
    "Machine Preacher Curl": ("accessory","optional"),
    "Single Arm Cable Curl": ("accessory","optional"),
    "Concentration Curl":    ("accessory","optional"),
    "Incline Dumbbell Curl": ("accessory","optional"),
    "Spider Curl":           ("accessory","optional"),
    "Zottman Curl":          ("accessory","optional"),
    "Drag Curl":             ("accessory","optional"),
    "Cable Hammer Curl":     ("accessory","optional"),
    "Band Bicep Curl":       ("accessory","optional"),
    "Barbell Reverse Curl":  ("accessory","optional"),
    "Reverse Cable Curl":    ("accessory","optional"),
    "Straight Arm Pulldown": ("accessory","optional"),
    "Single Arm Lat Pulldown":("accessory","optional"),
    "Close Grip Lat Pulldown":("accessory","optional"),
    "Dumbbell Pullover":     ("accessory","optional"),
    "Incline Dumbbell Fly":  ("accessory","optional"),
    "Low Cable Fly":         ("accessory","optional"),
    "High Cable Fly":        ("accessory","optional"),
    "Pec Deck":              ("accessory","optional"),
    "Chest Press Machine":   ("accessory","optional"),
    "Dumbbell Squeeze Press":("accessory","optional"),
    "Hip Abductor Machine":  ("accessory","optional"),
    "Hip Adductor Machine":  ("accessory","optional"),
    "Seated Leg Curl":       ("accessory","optional"),
    "Leg Press Calf Raise":  ("accessory","optional"),
    "Dumbbell Calf Raise":   ("accessory","optional"),
    "Donkey Calf Raise":     ("accessory","optional"),
    "Wall Sit":              ("accessory","optional"),
    "Russian Twist":         ("accessory","optional"),
    "Hollow Body Hold":      ("accessory","optional"),
    "Cable Woodchop":        ("accessory","optional"),
    "Knees to Chest":        ("accessory","optional"),
    "Band Lateral Walk":     ("accessory","optional"),
    "Wrist Curl":            ("accessory","optional"),
    "Wrist Extension":       ("accessory","optional"),
    "Hack Squat Machine":    ("compound", "secondary"),
}

# ── Parent relationships (variations pointing to their parent) ────────────────
PARENTS = {
    "Pause Squat":           "Back Squat",
    "Box Squat":             "Back Squat",
    "Safety Bar Squat":      "Back Squat",
    "Deficit Deadlift":      "Conventional Deadlift",
    "Rack Pull":             "Conventional Deadlift",
    "Paused Bench Press":    "Bench Press",
    "Decline Bench Press":   "Bench Press",
    "Close Grip Bench Press":"Bench Press",
    "Push Press":            "Overhead Press",
    "Push Jerk":             "Overhead Press",
    "Split Jerk":            "Push Jerk",
    "Dumbbell Romanian Deadlift":  "Romanian Deadlift",
    "Kettlebell Romanian Deadlift":"Romanian Deadlift",
    "Cable Romanian Deadlift":     "Romanian Deadlift",
    "Single Leg Romanian Deadlift":"Romanian Deadlift",
    "Dumbbell Hip Thrust":         "Hip Thrust",
    "Single Leg Hip Thrust":       "Hip Thrust",
    "Hip Thrust Machine":          "Hip Thrust",
    "Band Hip Thrust":             "Hip Thrust",
    "Single Leg Hip Thrust (Dumbbell)":"Hip Thrust",
    "Chin-Up":               "Pull-Up",
    "Neutral Grip Pull-Up":  "Pull-Up",
    "Ring Pull-Up":          "Pull-Up",
    "Assisted Pull-Up":      "Pull-Up",
    "Yates Row":             "Bent Over Row",
    "Pendlay Row":           "Bent Over Row",
    "Close Grip Lat Pulldown":"Lat Pulldown",
    "Single Arm Lat Pulldown":"Lat Pulldown",
    "Arnold Press":          "Dumbbell Shoulder Press",
    "Low Cable Fly":         "Cable Fly",
    "High Cable Fly":        "Cable Fly",
    "Hammer Curl":           "Dumbbell Curl",
    "Zottman Curl":          "Dumbbell Curl",
    "Spider Curl":           "Dumbbell Curl",
    "Incline Dumbbell Curl": "Dumbbell Curl",
    "Concentration Curl":    "Dumbbell Curl",
    "EZ Bar Skull Crusher":  "Barbell Skull Crusher",
    "Dumbbell Skull Crusher":"Barbell Skull Crusher",
    "Tricep Rope Pushdown":  "Tricep Pushdown",
    "Dumbbell Split Squat":  "Bulgarian Split Squat",
    "Barbell Lunge":         "Dumbbell Lunge",
    "Single Arm Kettlebell Swing":"Kettlebell Swing",
    "Hang Power Clean":      "Power Clean",
    "Clean":                 "Power Clean",
    "Hang Clean":            "Clean",
    "Clean and Jerk":        "Clean",
    "Hang Power Snatch":     "Power Snatch",
    "Snatch":                "Power Snatch",
    "Hang Snatch":           "Snatch",
    "Clean Pull":            "Power Clean",
    "Snatch Pull":           "Power Snatch",
    "Dumbbell Clean":        "Power Clean",
    "Kettlebell Clean and Press":"Kettlebell Clean",
    "Decline Dumbbell Press":"Dumbbell Bench Press",
    "Incline Dumbbell Fly":  "Dumbbell Fly",
}

# ── Equipment overrides (where multiple types are valid) ─────────────────────
EQUIPMENT_OVERRIDES = {
    "Goblet Squat":       ["dumbbell", "kettlebell"],
    "Bulgarian Split Squat": ["dumbbell", "barbell", "bodyweight"],
    "Farmer Walk":        ["dumbbell", "kettlebell"],
    "Suitcase Carry":     ["dumbbell", "kettlebell"],
    "Push Press":         ["barbell", "dumbbell", "kettlebell"],
    "Glute Bridge":       ["bodyweight", "barbell", "dumbbell"],
    "Nordic Hamstring Curl": ["bodyweight", "machine"],
    "T-Bar Row":          ["barbell", "machine"],
}

# ── Exercise to remove (duplicate) ──────────────────────────────────────────
REMOVE = {"Dumbbell Power Clean"}  # duplicate of Dumbbell Clean

# Extra aliases to merge from removed duplicates
ALIAS_MERGES = {
    "Dumbbell Clean": ["db power clean"],  # from removed Dumbbell Power Clean
}


def transform(exercises):
    result = []
    removed_names = set()

    for ex in exercises:
        name = ex["name"]
        if name in REMOVE:
            removed_names.add(name)
            continue

        out = dict(ex)

        # Equipment: string → array (or multi-array override)
        if name in EQUIPMENT_OVERRIDES:
            out["equipment"] = EQUIPMENT_OVERRIDES[name]
        else:
            # wrap single string in list
            eq = out.get("equipment")
            out["equipment"] = [eq] if eq else []

        # Muscle normalization
        if name in MUSCLE_OVERRIDES:
            out.update(MUSCLE_OVERRIDES[name])

        # Category + tier
        if name in CATEGORY_TIER:
            out["category"], out["tier"] = CATEGORY_TIER[name]
        else:
            # fallback heuristic
            mp = out.get("movement_pattern", "")
            out["category"] = "compound" if mp in ("squat", "hinge", "pull", "push", "carry") else "accessory"
            out["tier"] = "optional"

        # Parent
        out["parent"] = PARENTS.get(name, None)

        # Merge extra aliases
        if name in ALIAS_MERGES:
            existing = out.get("aliases", [])
            for a in ALIAS_MERGES[name]:
                if a not in existing:
                    existing.append(a)
            out["aliases"] = existing

        result.append(out)

    return result, removed_names


def main():
    with open(SRC) as f:
        exercises = json.load(f)

    print(f"Input: {len(exercises)} exercises")

    transformed, removed = transform(exercises)

    print(f"Removed (duplicates): {removed}")
    print(f"Output: {len(transformed)} exercises")

    # Stats
    categories = {}
    tiers = {}
    muscles = {}
    bad_muscles = set()
    VALID_MUSCLES = {
        "quads","hamstrings","glutes","calves","chest","lats","mid_back","erectors",
        "traps","anterior_delts","lateral_delts","posterior_delts","biceps","triceps",
        "forearms","abs","obliques","hip_flexors",
    }
    for ex in transformed:
        categories[ex["category"]] = categories.get(ex["category"], 0) + 1
        tiers[ex["tier"]] = tiers.get(ex["tier"], 0) + 1
        pm = ex.get("primary_muscle", "")
        if pm not in VALID_MUSCLES:
            bad_muscles.add(f"{ex['name']}: primary={pm}")
        for sm in ex.get("secondary_muscles", []):
            if sm not in VALID_MUSCLES:
                bad_muscles.add(f"{ex['name']}: secondary={sm}")
        muscles[pm] = muscles.get(pm, 0) + 1

    print(f"\nCategory breakdown: {categories}")
    print(f"Tier breakdown: {tiers}")
    print(f"Primary muscle distribution: {dict(sorted(muscles.items(), key=lambda x: -x[1]))}")
    if bad_muscles:
        print(f"\n⚠️  Invalid muscle terms found:")
        for b in sorted(bad_muscles):
            print(f"  {b}")
    else:
        print("\n✓ All muscle terms valid")

    # Duplicates report
    print("\n── Duplicates removed ──────────────────────────────")
    for r in sorted(removed):
        print(f"  {r}")

    # Variations report
    print("\n── Variations (have parent) ────────────────────────")
    for ex in transformed:
        if ex.get("parent"):
            print(f"  {ex['name']} → {ex['parent']}")

    # Write output
    with open(SRC, 'w') as f:
        json.dump(transformed, f, indent=2)
    print(f"\n✓ Written to {SRC}")


if __name__ == "__main__":
    main()
