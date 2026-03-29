---
name: godot_multiplayer
description: Godot 4 multiplayer authority model, RPC security, synchronizer setup, and server-authoritative patterns
tags: [godot, multiplayer, networking, rpc, game-dev]
source: agency-agents/game-development/godot/godot-multiplayer-engineer.md
---

## Godot Multiplayer Engineering

> ~2600 tokens

### Authority Model Rules

- The server (peer ID 1) owns all gameplay-critical state -- position, health, score, item state
- Set multiplayer authority explicitly with `node.set_multiplayer_authority(peer_id)` -- never rely on the default
- `is_multiplayer_authority()` must guard all state mutations -- never modify replicated state without this check
- Clients send input requests via RPC -- the server processes, validates, and updates authoritative state
- Set `multiplayer_authority` on every dynamically spawned node immediately after `add_child()`

### RPC Rules and Security

- `@rpc("any_peer")` -- any peer can call; use only for client-to-server requests that the server validates
- `@rpc("authority")` -- only the multiplayer authority can call; use for server-to-client confirmations
- `@rpc("call_local")` -- also runs locally; use for effects the caller should also experience
- Never use `@rpc("any_peer")` for functions that modify gameplay state without server-side validation inside the function body
- All critical game events use `"reliable"` RPC mode

### MultiplayerSynchronizer Constraints

- Only add properties that genuinely need to sync to every peer, not server-side-only state
- Use `ReplicationConfig` visibility modes: `REPLICATION_MODE_ALWAYS`, `REPLICATION_MODE_ON_CHANGE`, `REPLICATION_MODE_NEVER`
- All property paths must be valid at the time the node enters the tree -- invalid paths cause silent failure
- Use `ON_CHANGE` mode for all non-physics-driven state
- The synchronizer broadcasts FROM the authority TO all others

### Server Setup Pattern (ENet)

```gdscript
# NetworkManager.gd -- Autoload
extends Node

const PORT := 7777
const MAX_CLIENTS := 8

signal player_connected(peer_id: int)
signal player_disconnected(peer_id: int)
signal server_disconnected

func create_server() -> Error:
    var peer := ENetMultiplayerPeer.new()
    var error := peer.create_server(PORT, MAX_CLIENTS)
    if error != OK:
        return error
    multiplayer.multiplayer_peer = peer
    multiplayer.peer_connected.connect(_on_peer_connected)
    multiplayer.peer_disconnected.connect(_on_peer_disconnected)
    return OK

func join_server(address: String) -> Error:
    var peer := ENetMultiplayerPeer.new()
    var error := peer.create_client(address, PORT)
    if error != OK:
        return error
    multiplayer.multiplayer_peer = peer
    multiplayer.server_disconnected.connect(_on_server_disconnected)
    return OK

func disconnect_from_network() -> void:
    multiplayer.multiplayer_peer = null

func _on_peer_connected(peer_id: int) -> void:
    player_connected.emit(peer_id)

func _on_peer_disconnected(peer_id: int) -> void:
    player_disconnected.emit(peer_id)

func _on_server_disconnected() -> void:
    server_disconnected.emit()
    multiplayer.multiplayer_peer = null
```

### Server-Authoritative Player Controller

```gdscript
# Player.gd
extends CharacterBody2D

var _server_position: Vector2 = Vector2.ZERO
var _health: float = 100.0

@onready var synchronizer: MultiplayerSynchronizer = $MultiplayerSynchronizer

func _ready() -> void:
    set_multiplayer_authority(name.to_int())

func _physics_process(delta: float) -> void:
    if not is_multiplayer_authority():
        return
    var input_dir := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
    velocity = input_dir * 200.0
    move_and_slide()

# Client sends input to server
@rpc("any_peer", "unreliable")
func send_input(direction: Vector2) -> void:
    if not multiplayer.is_server():
        return
    var sender_id := multiplayer.get_remote_sender_id()
    if sender_id != get_multiplayer_authority():
        return  # Reject: wrong peer sending input for this player
    velocity = direction.normalized() * 200.0
    move_and_slide()

# Server confirms a hit to all clients
@rpc("authority", "reliable", "call_local")
func take_damage(amount: float) -> void:
    _health -= amount
    if _health <= 0.0:
        _on_died()
```

### MultiplayerSpawner Setup

```gdscript
# GameWorld.gd -- on the server
extends Node2D

@onready var spawner: MultiplayerSpawner = $MultiplayerSpawner

func _ready() -> void:
    if not multiplayer.is_server():
        return
    spawner.spawn_path = NodePath(".")

    NetworkManager.player_connected.connect(_on_player_connected)
    NetworkManager.player_disconnected.connect(_on_player_disconnected)

func _on_player_connected(peer_id: int) -> void:
    var player := preload("res://scenes/Player.tscn").instantiate()
    player.name = str(peer_id)  # Name = peer ID for authority lookup
    add_child(player)           # MultiplayerSpawner auto-replicates to all peers
    player.set_multiplayer_authority(peer_id)

func _on_player_disconnected(peer_id: int) -> void:
    var player := get_node_or_null(str(peer_id))
    if player:
        player.queue_free()  # MultiplayerSpawner auto-removes on peers
```

### RPC Security Audit Checklist

Review every `@rpc("any_peer")` function against these checks:

- [ ] Function starts with `if not multiplayer.is_server(): return` guard
- [ ] Sender ID retrieved via `multiplayer.get_remote_sender_id()`
- [ ] Sender validated: is this the correct peer for this action?
- [ ] Input validated: are the values within plausible bounds?
- [ ] Target validated: does the referenced entity exist (`is_instance_valid()`)?
- [ ] Proximity/context validated: is the player close enough / in the right state?
- [ ] No state mutation before all validation passes
- [ ] Confirmation sent back to client via `@rpc("authority")` after success

#### RPC Security Pattern Example

```gdscript
@rpc("any_peer", "reliable")
func request_pick_up_item(item_id: int) -> void:
    if not multiplayer.is_server():
        return

    var sender_id := multiplayer.get_remote_sender_id()
    var player := get_player_by_peer_id(sender_id)
    if not is_instance_valid(player):
        return

    var item := get_item_by_id(item_id)
    if not is_instance_valid(item):
        return

    # Validate: is the player close enough?
    if player.global_position.distance_to(item.global_position) > 100.0:
        return

    _give_item_to_player(player, item)
    confirm_item_pickup.rpc(sender_id, item_id)

@rpc("authority", "reliable")
func confirm_item_pickup(peer_id: int, item_id: int) -> void:
    if multiplayer.get_unique_id() == peer_id:
        UIManager.show_pickup_notification(item_id)
```

### Workflow Process

1. **Architecture Planning** -- Choose topology (client-server vs P2P). Define server-owned vs peer-owned nodes. Map all RPCs: who calls, who executes, what validation required.
2. **Network Manager Setup** -- Build `NetworkManager` Autoload with create/join/disconnect. Wire `peer_connected` and `peer_disconnected` to spawn/despawn logic.
3. **Scene Replication** -- Add `MultiplayerSpawner` to root world node. Add `MultiplayerSynchronizer` to every networked entity. Configure synchronized properties with `ON_CHANGE` mode.
4. **Authority Setup** -- Set `multiplayer_authority` on every spawned node after `add_child()`. Guard all mutations with `is_multiplayer_authority()`. Test by printing authority on both server and client.
5. **RPC Security Audit** -- Review every `@rpc("any_peer")` with validation checklist. Test with impossible values. Test cross-client RPC spoofing.
6. **Latency Testing** -- Simulate 100ms and 200ms latency on local loopback. Verify critical events use `"reliable"` mode. Test reconnection: client drops and rejoins.

### Scene Spawning Rules

- Use `MultiplayerSpawner` for all dynamically spawned networked nodes -- manual `add_child()` on networked nodes desynchronizes peers
- All scenes spawned by `MultiplayerSpawner` must be registered in its `spawn_path` list before use
- `MultiplayerSpawner` auto-spawns only on the authority node -- non-authority peers receive the node via replication
- Handle disconnection cleanup: remove orphaned player nodes on `peer_disconnected`
