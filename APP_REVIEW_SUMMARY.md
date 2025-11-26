# OracleBox App - Comprehensive Layout & Code Review
**Date:** November 26, 2025

## ✅ Layout Consistency Check

### Logo Implementation (All Pages)
- ✅ **Connection Page**: `@mipmap/sqlogo_foreground` - 96dp x 96dp, scale 2.5x
- ✅ **Mode Selection**: `@mipmap/sqlogo_foreground` - 72dp x 72dp, scale 2x
- ✅ **Spirit Box**: `@mipmap/sqlogo_foreground` - 72dp x 72dp, scale 2x
- ✅ **REM Pod**: `@mipmap/sqlogo_foreground` - 72dp x 72dp, scale 2x
- ✅ **Music Box**: `@mipmap/sqlogo_foreground` - 72dp x 72dp, scale 2x
- ✅ **Device Settings**: `@mipmap/sqlogo_foreground` - 72dp x 72dp, scale 2x

### OracleBox Text (All Mode Pages)
- ✅ All pages show "OracleBox" text below logo
- ✅ Consistent styling: 18sp, #D7B972 color, bold
- ✅ Consistent margin: 8dp top margin

### Spacing Consistency
- ✅ All mode pages: 22dp Space before logo
- ✅ All mode pages: 16dp margin top on logo
- ✅ All mode pages: 8dp margin top on text

### Header Structure (All Mode Pages)
- ✅ **Spirit Box**: Integrated header with back button (button_back_to_modes_sb)
- ✅ **REM Pod**: Integrated header with back button (button_back_to_modes)
- ✅ **Music Box**: Integrated header with back button (button_back_to_modes_mb)
- ✅ **Device Settings**: Integrated header with back button (button_back_to_modes_ds)
- ✅ **Mode Selection**: Integrated header with back button (button_back_to_connection)

## ✅ Code Quality Check

### Compilation Status
- ✅ **No errors found** in entire app module
- ✅ All XML layouts valid
- ✅ All Kotlin files compile successfully

### Back Button Functionality
- ✅ **ConnectionActivity**: No back button (root activity)
- ✅ **ModeSelectionActivity**: Back to connection with slide transition
- ✅ **ControlActivity**: Back to modes with fade transition
- ✅ **RemPodActivity**: Back to modes with fade transition
- ✅ **MusicBoxActivity**: Back to modes with fade transition
- ✅ **DeviceSettingsActivity**: Back to modes with slide transition

### Page Transitions
- ✅ Connection → Mode Selection: `slide_in_right, slide_out_left`
- ✅ Mode Selection → Spirit Box: `fade_in_static, fade_out_static`
- ✅ Mode Selection → REM Pod: `fade_in_static, fade_out_static`
- ✅ Mode Selection → Music Box: `fade_in_static, fade_out_static`
- ✅ Mode Selection → Device Settings: `slide_in_right, slide_out_left`
- ✅ All back buttons: Reverse animations

### Voice Announcement System
- ✅ **Mode Selection**: Plays "choose_method.wav" on load
- ✅ **Spirit Box**: Announces "spirit_box.wav" before navigation
- ✅ **REM Pod**: Announces "rempod.wav" before navigation
- ✅ **Music Box**: Announces "music_box.wav" before navigation
- ✅ All announcements stored in `/home/dylan/oraclebox/announcements/`
- ✅ Separate from user-uploadable sounds in `/home/dylan/oraclebox/sounds/`

### Start Button Implementation
- ✅ **Spirit Box**: "START SPIRIT BOX" button (gold background, 18sp)
  - Hides sweep controls initially
  - Shows controls when pressed
  - Button disappears after activation
  - Uses clean ID-based show/hide: `layout_status_cards`, `layout_sweep_buttons`, `layout_direction_buttons`
- ✅ **REM Pod**: "ARM REM POD" button already implemented
- ✅ **Music Box**: "START MUSIC BOX" button already implemented

## ✅ Auto-Connect System
- ✅ **SavedPreferences**: MAC address stored in SharedPreferences
- ✅ **Auto-connect**: Attempts connection on app launch
- ✅ **Loading Animation**: Pulsing logo during connection
- ✅ **Swoop Transition**: Zoom effect on successful connection
- ✅ **Disconnect**: Clears saved device preference

## ✅ Development Notices
- ✅ **REM Pod**: Shows development notice dialog on entry
- ✅ **Music Box**: Shows development notice dialog on entry
- ✅ Both dialogs require user acknowledgment

## ✅ Startup Sound Management
- ✅ **Location**: Moved from Spirit Box to Device Settings
- ✅ **Full Controls**: Upload, play, refresh, set, clear
- ✅ **Progress Bar**: Upload progress tracking
- ✅ **Sound List**: Spinner with all available sounds
- ✅ **Spirit Box**: Cleaned up (sound controls removed)

## 📁 File Organization

### Android App Structure
```
app/src/main/
├── java/com/apx/oraclebox/
│   ├── ui/
│   │   ├── connection/
│   │   │   ├── ConnectionActivity.kt ✅
│   │   │   └── ConnectionViewModel.kt ✅
│   │   ├── mode/
│   │   │   └── ModeSelectionActivity.kt ✅
│   │   ├── control/
│   │   │   └── ControlActivity.kt ✅ (Spirit Box)
│   │   ├── rempod/
│   │   │   └── RemPodActivity.kt ✅
│   │   ├── musicbox/
│   │   │   └── MusicBoxActivity.kt ✅
│   │   └── settings/
│   │       └── DeviceSettingsActivity.kt ✅
│   └── ...
└── res/
    ├── layout/
    │   ├── activity_connection.xml ✅
    │   ├── activity_mode_selection.xml ✅
    │   ├── activity_control.xml ✅
    │   ├── activity_rempod.xml ✅
    │   ├── activity_musicbox.xml ✅
    │   └── activity_device_settings.xml ✅
    └── anim/
        ├── pulse_logo.xml ✅
        ├── zoom_swoop.xml ✅
        ├── slide_in_right.xml ✅
        ├── slide_out_left.xml ✅
        ├── slide_in_left.xml ✅
        ├── slide_out_right.xml ✅
        ├── fade_in_static.xml ✅
        └── fade_out_static.xml ✅
```

### Raspberry Pi Structure
```
~/oraclebox/
├── announcements/          # System voice files (not changeable via app)
│   ├── choose_method.wav   # 1.1M - tempo 1.0 (normal speed)
│   ├── spirit_box.wav      # 610K - tempo 1.0
│   ├── rempod.wav          # 590K - tempo 1.0
│   └── music_box.wav       # 635K - tempo 1.0
├── sounds/                 # User-uploadable sounds
│   └── welcome_oracle_box.wav
├── oraclebox_merged.py     # Backend with ANNOUNCEMENTS_DIR support
└── config.json
```

## 🎨 Design System

### Color Palette
- **Gothic Gold**: `#D7B972` - Headers, titles, OracleBox text
- **Ghost Surface**: Various tones for cards and text
- **Bakelite**: Background for buttons and cards
- **Wood Background**: `@drawable/wood_bg` with tint `#784A38`

### Typography
- **Page Titles**: 20sp, bold, gothic_gold
- **OracleBox Text**: 18sp, bold, #D7B972
- **Button Text**: 14sp (large buttons), 10-11sp (small buttons)
- **Status Text**: 10sp (labels), 14-18sp (values)

### Animations
- **Slide**: 400ms, direction-based (dial turning metaphor)
- **Fade Static**: 300ms, scale effect (tuning frequency metaphor)
- **Pulse**: 1500ms, repeating (breathing/loading effect)
- **Swoop**: 500ms, 3x zoom + fade (portal effect)

## 🎯 User Flow Summary

```
App Launch
    ↓
ConnectionActivity (Landing Page)
    ↓ (Auto-connect if saved device found)
    ↓ (Plays welcome_oracle_box.wav)
    ↓ (Swoop animation on success)
    ↓
ModeSelectionActivity
    ↓ (Plays choose_method.wav)
    ↓ (User selects mode)
    ↓ (Announces selected mode)
    ↓
┌───────────────────┬─────────────────┬──────────────────┬──────────────────┐
│   Spirit Box      │    REM Pod      │   Music Box      │ Device Settings  │
│ (ControlActivity) │(RemPodActivity) │(MusicBoxActivity)│(DeviceSettings)  │
│                   │                 │                  │                  │
│ START SPIRIT BOX  │   ARM REM POD   │ START MUSIC BOX  │ Startup Sounds   │
│ (shows controls)  │ (dev notice)    │ (dev notice)     │ Pi Config        │
│                   │                 │                  │ BT Audio         │
│ ◀ BACK            │  ◀ BACK         │  ◀ BACK          │ ◀ BACK           │
└───────────────────┴─────────────────┴──────────────────┴──────────────────┘
    ↓ (All back buttons return to Mode Selection)
    ↓
ModeSelectionActivity
    ↓ (DISCONNECT button)
    ↓ (Clears saved device)
    ↓
ConnectionActivity
```

## ✅ Final Status

**All systems operational and consistent:**
- ✅ No compilation errors
- ✅ Uniform layouts across all pages
- ✅ Consistent design system
- ✅ Smooth page transitions
- ✅ Voice announcement system
- ✅ Auto-connect functionality
- ✅ Start button flow
- ✅ Clean code organization
- ✅ Proper file separation (system vs user sounds)

**Ready for build and deployment! 🚀**
