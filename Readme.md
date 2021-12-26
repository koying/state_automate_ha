# Integration to simulate Logitech activities

This component is a mix between scenes an automations.
It aims to replicate the Logitech Harmonu activity conecept.

## HA Configuration

In your configuration.yaml:

```yaml
state_automate:
  - entity_id: <remote sensor entity>
    activities: !include_dir_list state_automate/<remote sensor entity>
```

## YAML activities

```yaml
name: "Test 1"
states:
  - enter:
    - service: light.turn_on
      target:
        entity_id: light.wled_bureau
      data:
        rgb_color: [0,0,255]
  - 105:
    - service: light.turn_on
      target:
        entity_id: light.wled_bureau
      data:
        rgb_color: [255,0,0]
  - 106:
    - service: light.turn_on
      target:
        entity_id: light.wled_bureau
      data:
        rgb_color: [0,255,0]
```

### Special states

`enter`: Actions to be executed when the activity is selected  
`leave`: Actions to be executed when the activity is deselected  
