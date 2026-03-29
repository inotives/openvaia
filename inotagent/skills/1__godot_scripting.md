---
name: godot_scripting
description: GDScript 2.0 static typing, signal conventions, node composition, autoload rules, and scene lifecycle for Godot 4
tags: [godot, gdscript, signals, composition, game-dev]
source: agency-agents/game-development/godot/godot-gameplay-scripter.md
---

## Godot Gameplay Scripting

> ~2400 tokens

### GDScript 2.0 Static Typing Rules

- Every variable, function parameter, and return type must be explicitly typed -- no untyped `var` in production code
- Use `:=` for inferred types only when the type is unambiguous from the right-hand expression
- Typed arrays (`Array[EnemyData]`, `Array[Node]`) must be used everywhere -- untyped arrays lose editor autocomplete and runtime validation
- Use `@export` with explicit types for all inspector-exposed properties
- Enable `strict mode` to surface type errors at parse time, not runtime
- Enable all warnings: `gdscript/warnings/enable_all_warnings=true` in `project.godot`
- Replace all `get_node("path")` with `@onready` typed variables

### Signal Naming Conventions

- Signal names must be `snake_case` (e.g., `health_changed`, `enemy_died`, `item_collected`)
- Signals must carry typed parameters -- never emit untyped `Variant` unless interfacing with legacy code
- Document each signal with `##` doc comments
- A script must `extend` at least `Object` (or any Node subclass) to use the signal system
- Never connect a signal to a method that does not exist at connection time

### Node Composition Architecture

- Follow "everything is a node" -- behavior is composed by adding nodes, not by multiplying inheritance depth
- Prefer composition over inheritance: a `HealthComponent` node attached as a child is better than a `CharacterWithHealth` base class
- Every scene must be independently instanciable -- no assumptions about parent node type or sibling existence
- Use `@onready` for node references with explicit types:
  ```gdscript
  @onready var health_bar: ProgressBar = $UI/HealthBar
  ```
- Access sibling/parent nodes via exported `NodePath` variables, not hardcoded `get_node()` paths
- Components communicate upward via signals, never downward via `get_parent()` or `owner`
- Every node component < 200 lines handling exactly one gameplay concern

### Autoload Rules

- Autoloads are singletons -- use only for genuine cross-scene global state: settings, save data, event buses, input maps
- Never put gameplay logic in an Autoload -- it cannot be instanced, tested in isolation, or garbage collected between scenes
- Prefer a signal bus Autoload (`EventBus.gd`) over direct node references for cross-scene communication
- Document every Autoload's purpose and lifetime in a comment at the top of the file

### Scene Tree Lifecycle

- Use `_ready()` for initialization that requires the node to be in the scene tree -- never in `_init()`
- Disconnect signals in `_exit_tree()` or use `connect(..., CONNECT_ONE_SHOT)` for fire-and-forget connections
- Use `queue_free()` for safe deferred node removal -- never `free()` on a node that may still be processing
- Test every scene in isolation by running it directly (F6) -- must not crash without parent context
- No `_process()` functions polling state that could be signal-driven

### Signal Bus Pattern

```gdscript
## Global event bus for cross-scene, decoupled communication.
## Add signals here only for events that genuinely span multiple scenes.
extends Node

signal player_died
signal score_changed(new_score: int)
signal level_completed(level_id: String)
signal item_collected(item_id: String, collector: Node)
```

### Typed Signal Declaration (HealthComponent)

```gdscript
class_name HealthComponent
extends Node

## Emitted when health value changes. [param new_health] is clamped to [0, max_health].
signal health_changed(new_health: float)

## Emitted once when health reaches zero.
signal died

@export var max_health: float = 100.0

var _current_health: float = 0.0

func _ready() -> void:
    _current_health = max_health

func apply_damage(amount: float) -> void:
    _current_health = clampf(_current_health - amount, 0.0, max_health)
    health_changed.emit(_current_health)
    if _current_health == 0.0:
        died.emit()

func heal(amount: float) -> void:
    _current_health = clampf(_current_health + amount, 0.0, max_health)
    health_changed.emit(_current_health)
```

### Resource-Based Data (ScriptableObject Equivalent)

```gdscript
## Defines static data for an enemy type. Create via right-click > New Resource.
class_name EnemyData
extends Resource

@export var display_name: String = ""
@export var max_health: float = 100.0
@export var move_speed: float = 150.0
@export var damage: float = 10.0
@export var sprite: Texture2D

# Usage: export from any node
# @export var enemy_data: EnemyData
```

### Composition-Based Player Example

```gdscript
class_name Player
extends CharacterBody2D

# Composed behavior via child nodes -- no inheritance pyramid
@onready var health: HealthComponent = $HealthComponent
@onready var movement: MovementComponent = $MovementComponent
@onready var animator: AnimationPlayer = $AnimationPlayer

func _ready() -> void:
    health.died.connect(_on_died)
    health.health_changed.connect(_on_health_changed)

func _physics_process(delta: float) -> void:
    movement.process_movement(delta)
    move_and_slide()

func _on_died() -> void:
    animator.play("death")
    set_physics_process(false)
    EventBus.player_died.emit()

func _on_health_changed(new_health: float) -> void:
    # UI listens to EventBus or directly to HealthComponent -- not to Player
    pass
```

### Typed Array and Safe Node Access

```gdscript
## Spawner that tracks active enemies with a typed array.
class_name EnemySpawner
extends Node2D

@export var enemy_scene: PackedScene
@export var max_enemies: int = 10

var _active_enemies: Array[EnemyBase] = []

func spawn_enemy(position: Vector2) -> void:
    if _active_enemies.size() >= max_enemies:
        return
    var enemy := enemy_scene.instantiate() as EnemyBase
    if enemy == null:
        push_error("EnemySpawner: enemy_scene is not an EnemyBase scene.")
        return
    add_child(enemy)
    enemy.global_position = position
    enemy.died.connect(_on_enemy_died.bind(enemy))
    _active_enemies.append(enemy)

func _on_enemy_died(enemy: EnemyBase) -> void:
    _active_enemies.erase(enemy)
```

### Workflow Process

1. **Scene Architecture** -- Define self-contained instanced units vs. root-level worlds. Map cross-scene communication through EventBus. Identify shared data for Resource files vs. node state.
2. **Signal Architecture** -- Define all signals upfront with typed parameters (treat as public API). Document with `##` comments. Validate naming conventions before wiring.
3. **Component Decomposition** -- Break monolithic scripts into `HealthComponent`, `MovementComponent`, `InteractionComponent`, etc. Each exports its own config. Communicate upward via signals only.
4. **Static Typing Audit** -- Eliminate all untyped `var` in gameplay code. Replace all `get_node("path")` with `@onready` typed variables.
5. **Autoload Hygiene** -- Remove Autoloads containing gameplay logic (move to instanced scenes). Prune EventBus signals only used within one scene.
6. **Isolation Testing** -- Run every scene standalone with F6. Write `@tool` scripts for editor-time validation. Use `assert()` for invariant checking.
