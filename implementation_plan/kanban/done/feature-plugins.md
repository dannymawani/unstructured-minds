# Plugin/Extension System

**Phase:** 5 - Extensibility
**Priority:** Low
**Status:** Not Started

## Description

Create a plugin architecture for extending functionality without modifying core code.

## Tasks

- [ ] Plugin API definition
- [ ] Plugin loading mechanism
- [ ] Plugin settings UI
- [ ] Built-in plugin examples
- [ ] Plugin marketplace concept
- [ ] Plugin sandboxing

## Acceptance Criteria

- Plugins can add new features
- Plugins isolated from core
- Easy to enable/disable
- Settings per plugin
- Clear API documentation

## Plugin Types

1. **Themes**: Custom color schemes
2. **Commands**: New slash commands
3. **Extractors**: Custom data extractors
4. **Widgets**: Dashboard widgets
5. **Integrations**: External services

## Plugin API

```typescript
interface Plugin {
  name: string;
  version: string;

  // Lifecycle
  onLoad(): Promise<void>;
  onUnload(): Promise<void>;

  // Extension points
  commands?: Command[];
  extractors?: Extractor[];
  widgets?: Widget[];
  settings?: SettingsSchema;
}
```

## Example: Weather Plugin

```typescript
export default {
  name: "weather",
  version: "1.0.0",

  commands: [{
    name: "weather",
    description: "Add weather to daily note",
    execute: async (ctx) => {
      const weather = await fetchWeather(ctx.settings.location);
      return `Weather: ${weather.temp}°F, ${weather.condition}`;
    }
  }],

  settings: {
    location: { type: "string", default: "auto" }
  }
};
```
