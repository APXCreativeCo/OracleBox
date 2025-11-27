# OracleBox Bluetooth Architecture

## Overview
The OracleBox app uses Classic Bluetooth SPP (Serial Port Profile) over RFCOMM channel 1 to communicate with the Raspberry Pi. The architecture implements a singleton pattern to maintain a single persistent connection across all activities.

## Connection Flow

### 1. Initial Connection (ConnectionActivity)
- User selects paired Bluetooth device from list
- Device address and name are passed via Intent extras to ModeSelectionActivity
- No actual Bluetooth connection is established at this stage
- Device info is saved to SharedPreferences for auto-reconnect on next launch

### 2. Connection Establishment (ControlViewModel)
When any activity creates a ControlViewModel:

```kotlin
// Singleton repository pattern
private val repo: BluetoothRepository? = run {
    val existing = OracleBoxApplication.getBluetoothRepository(deviceAddress)
    if (existing != null && existing.isConnected()) {
        existing  // Reuse existing connection
    } else {
        adapter?.let {
            val newRepo = BluetoothRepository(application.applicationContext, it)
            OracleBoxApplication.setBluetoothRepository(newRepo)
            newRepo  // Will connect in init block
        }
    }
}

init {
    connectIfNeeded()  // Connects if not already connected
}
```

### 3. Connection Lifecycle

**connectIfNeeded()** logic:
1. If repository already connected → Update UI, start line listener, return
2. If not connected → Get BluetoothDevice from address, call connectToDevice()
3. On success → Set `_disconnected` to false, start listening for incoming lines
4. On failure → Set `_disconnected` to true, show error message

**Connection persistence:**
- Single BluetoothRepository instance stored in OracleBoxApplication companion object
- Connection maintained across activity navigation (Mode Selection → Spirit Box → Device Settings, etc.)
- ViewModels check `isConnected()` before reusing repository
- If connection drops, ViewModel reconnects automatically

**Disconnect scenarios:**
1. **User clicks Disconnect button** → Calls `OracleBoxApplication.clearBluetoothRepository()` which:
   - Calls `repository.disconnect()`
   - Sets singleton to null
   - Navigates back to ConnectionActivity
   
2. **Connection error/timeout** → Sets `_disconnected` to true, shows error banner
   
3. **App fully closed** → Bluetooth socket automatically closes (OS handles cleanup)

## Architecture Components

### BluetoothClient (Low-level socket management)
**Location:** `app/src/main/java/com/apx/oraclebox/bt/BluetoothClient.kt`

**Responsibilities:**
- Direct RFCOMM socket on channel 1 (no SDP/SPP UUID required)
- Uses reflection to call `createRfcommSocket(1)` for Pi compatibility
- Manages BufferedReader/PrintWriter for line-based communication
- Background coroutine for receiving lines via Channel
- Thread-safe connection state with AtomicBoolean

**Key methods:**
- `connect(device: BluetoothDevice)` - Establishes socket, starts receive loop
- `disconnect()` - Closes socket, cancels receive job
- `sendCommandAndReadLine(command: String): String` - Blocking send/receive
- `isConnectedFlag: Boolean` - Thread-safe connection status

### BluetoothRepository (Protocol & commands)
**Location:** `app/src/main/java/com/apx/oraclebox/bt/BluetoothRepository.kt`

**Responsibilities:**
- Wraps BluetoothClient with OracleBox-specific protocol
- Parses JSON responses (STATUS, PING, SOUND LIST, etc.)
- Maintains log of sent/received commands
- Provides suspend functions for all OracleBox commands

**Key methods:**
- `connectToDevice(device: BluetoothDevice)` - Delegates to BluetoothClient
- `isConnected(): Boolean` - Returns client connection status
- `sendRawCommand(command: String): OracleBoxResponse` - Send command, parse response
- `requestStatus(): OracleBoxStatus?` - Get full device state
- Sweep commands: `startSweep()`, `stopSweep()`, `setSpeed()`, `faster()`, `slower()`
- Direction: `setDirectionUp()`, `setDirectionDown()`, `toggleDirection()`
- LEDs: `setSweepLedMode()`, `setBoxLedMode()`, `allLedsOff()`
- Audio FX: `fxStatus()`, `fxEnable()`, `fxDisable()`, `fxSet()`, `fxPresetSet()`
- Mixer: `mixerStatus()`, `setSpeakerVolume()`, `setMicVolume()`, `setAutoGain()`
- Sounds: `listSounds()`, `playSound()`, `setStartupSound()`

### OracleBoxApplication (Singleton holder)
**Location:** `app/src/main/java/com/apx/oraclebox/OracleBoxApplication.kt`

**Responsibilities:**
- Application-scope lifecycle (registered in AndroidManifest)
- Holds single BluetoothRepository instance in companion object
- Provides static methods for get/set/clear repository

**Registered in AndroidManifest.xml:**
```xml
<application
    android:name=".OracleBoxApplication"
    ...>
```

**API:**
```kotlin
fun getBluetoothRepository(deviceAddress: String?): BluetoothRepository?
fun setBluetoothRepository(repo: BluetoothRepository?)
fun clearBluetoothRepository()  // Disconnects and clears singleton
```

### ControlViewModel (Shared across activities)
**Location:** `app/src/main/java/com/apx/oraclebox/ui/control/ControlViewModel.kt`

**Responsibilities:**
- Shared ViewModel used by: ModeSelectionActivity, ControlActivity, RemPodActivity, MusicBoxActivity
- Manages connection state via singleton repository
- Exposes LiveData for UI observation: status, logs, disconnected, errorMessage
- Implements all control commands (sweep, FX, mixer, LEDs, sounds)
- Handles HTTP uploads for larger files (sound files, firmware updates)

**LiveData properties:**
- `status: LiveData<OracleBoxStatus>` - Current device state (speed, direction, running, LEDs)
- `logs: LiveData<List<LogEntry>>` - All Bluetooth communication logs
- `disconnected: LiveData<Boolean>` - Connection state (true = show error banner)
- `errorMessage: LiveData<String>` - Last error for Toast display
- `fxUiState: LiveData<FxUiState>` - Audio effects state
- `mixerUiState: LiveData<MixerUiState>` - Audio mixer state

**Factory pattern:**
```kotlin
class Factory(
    private val application: Application,
    private val deviceAddress: String?
) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        return ControlViewModel(application, deviceAddress) as T
    }
}
```

## Error Handling

### Connection Errors
All command methods check `isConnected()` before execution:
```kotlin
if (!localRepo.isConnected()) {
    _errorMessage.value = "Not connected to OracleBox."
    _disconnected.value = true
    return@launch
}
```

### Command Errors
All Bluetooth operations wrapped in try-catch:
```kotlin
try {
    withContext(Dispatchers.IO) {
        block(localRepo)
    }
} catch (e: Exception) {
    _errorMessage.value = e.message
    _disconnected.value = true
} finally {
    refreshLogs()
}
```

### UI Feedback
- **Red banner**: Shows "DISCONNECTED FROM ORACLEBOX" when `disconnected == true`
- **Toast messages**: Shows error message from `errorMessage` LiveData
- **Loading states**: FxUiState and MixerUiState have `loading` flag
- **Button states**: Disabled when not connected

## Pi-Side Protocol

### Command Format
```
COMMAND [ARG1] [ARG2]\n
```

### Response Format
```
OK [OPTIONAL JSON PAYLOAD]\n
ERR [ERROR MESSAGE]\n
```

### Example: STATUS command
**Send:** `STATUS\n`
**Receive:** 
```json
OK {"speed_ms": 150, "direction": "up", "running": true, "sweep_led_mode": "on", "box_led_mode": "breath", "startup_sound": "welcome.wav"}
```

### Example: START command
**Send:** `START\n`
**Receive:** `OK\n`

### Voice Announcements
Pi plays voice announcements when commands are received:
- Announcements stored in `/home/dylan/oraclebox/announcements/`
- FX processing pauses during playback to avoid audio device conflicts
- App sends commands when appropriate (e.g., "select_your_mode.wav" on Mode Selection page)

## Testing Checklist

### ✅ Connection Initialization
- [x] First activity creates repository and connects
- [x] Subsequent activities reuse existing connection
- [x] connectIfNeeded() only connects if not already connected
- [x] Connection errors are caught and reported

### ✅ Connection Persistence
- [x] Navigate Mode Selection → Spirit Box → stays connected
- [x] Navigate Spirit Box → Device Settings → stays connected
- [x] Navigate back to Mode Selection → still connected
- [x] Connection persists across multiple activity lifecycle changes

### ✅ Disconnect Handling
- [x] Disconnect button clears singleton and closes socket
- [x] Connection errors set disconnected=true and show banner
- [x] Repository cleanup calls disconnect() on socket

### ✅ Error Handling
- [x] All commands check isConnected() first
- [x] Exceptions caught and shown to user
- [x] Connection drops detected and reported
- [x] UI shows appropriate error states

### ✅ State Management
- [x] LiveData observers update UI correctly
- [x] Status updates reflect actual device state
- [x] Logs show all Bluetooth traffic
- [x] FX and Mixer states synchronized

### ✅ Compilation
- [x] No compilation errors
- [x] All imports present
- [x] ViewModelProvider factories working
- [x] OracleBoxApplication registered in manifest

## Known Issues & Limitations

### RFCOMM Channel 1
The app uses direct RFCOMM channel 1 instead of SDP/SPP UUID discovery. This is intentional due to Pi configuration limitations but means:
- Device must have SPP service on channel 1
- Won't work with devices using different channel numbers
- No service discovery (UUID matching)

### Connection Recovery
If connection drops mid-session:
- User sees "DISCONNECTED" banner
- Must return to Mode Selection or Connection page
- App will attempt reconnect when ViewModel reinitializes
- No automatic retry mechanism currently implemented

### Background Disconnection
When app is backgrounded for extended period:
- Android may kill app process
- Bluetooth socket closes
- User must reconnect on next launch
- Auto-connect will trigger if device still paired

## Future Enhancements

1. **Auto-reconnect on connection loss**: Add retry logic when socket drops
2. **Connection timeout**: Add configurable timeout for connect attempts
3. **Background service**: Keep connection alive when app backgrounded
4. **Multi-device support**: Allow switching between multiple OracleBox devices
5. **Connection status notifications**: Show persistent notification when connected
6. **Diagnostic mode**: Expose raw Bluetooth logs for troubleshooting

## Debugging Tips

### Enable Bluetooth Logs
Check ControlViewModel logs LiveData:
```kotlin
viewModel.logs.observe(this) { logs ->
    logs.forEach { log ->
        Log.d("BT", "${log.direction}: ${log.text}")
    }
}
```

### Check Connection State
```kotlin
val isConnected = viewModel.repo?.isConnected() ?: false
Log.d("BT", "Connected: $isConnected")
```

### Test Commands in Terminal (Pi side)
```bash
# Listen for connections
sudo rfcomm watch 0 1

# Or check existing connection
sudo rfcomm show
```

### Monitor Pi Bluetooth
```bash
# Check Bluetooth service
sudo systemctl status bluetooth

# Check OracleBox service logs
sudo journalctl -u oraclebox.service -f

# Test serial connection
screen /dev/rfcomm0 115200
```
