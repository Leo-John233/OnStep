# OnStep 4.24 谐波赤道仪安全增强版

本项目基于 [OnStep 4.24](https://github.com/hjd1964/OnStep/tree/release-4.24) 修改

它不是一次简单的参数调整

这套固件来自谐波赤道仪的实际使用需求。原始 OnStep 4.24 面向多种赤道仪和经纬仪，默认行为更通用。这个分支则把重点放在 MaxESP3 谐波赤道仪的开机保持、位置可信、自动回零、限位脱困和客户端控制安全上

这版固件遵循一个很直接的原则

> 自动动作必须建立在可信位置上，手动动作要为排险留出通道

## 主要改进

| 使用场景 | 原始 OnStep 4.24 | 当前版本 |
| --- | --- | --- |
| 开机状态 | 按通用启动位置和跟踪配置运行 | 电机先保持，跟踪关闭，等待 Home 或 Set Home |
| 位置判断 | 主要依赖原有 Home 和运动状态 | 独立记录位置是否可信以及是否需要恢复 |
| 未回零 GOTO | 没有独立的开机回零策略 | GOTO、Sync、Park 和开启跟踪统一进入位置检查 |
| 手动移动 | 由原有导星和限位规则处理 | 未回零仍可手动移动，便于找零和排险 |
| 物理限位 | 触发后停止当前运动 | 记录危险方向，只拦截继续撞限位的一侧，允许反向脱困 |
| 自动回零 | 快速搜索和慢速精找两阶段 | 快速搜索、慢速精找、零位偏置三阶段 |
| 回零速度 | 固定使用 8 档和 7 档 | 快速、慢速、偏置速度都可在 `Config.h` 设置 |
| 回零失败 | 结束当前回零流程 | 明确将位置标记为不可信，不会把失败当作成功 |
| GOTO 中断 | 走通用停止和状态恢复流程 | 区分普通中止、物理限位和位置丢失，只有正常到达才进入成功流程 |
| 客户端首次连接 | Home 状态可能只来自内部位置标记 | `:GU#` 只有在 Home 且位置可信时才返回 `H` |
| TMC2209 细分切换 | 两个轴分别判断和切换 | MaxESP3 共享 M0 和 M1 时双轴同步切换，支持 64 细分跟踪和 32 细分 GOTO |
| 配置体验 | 英文通用配置 | 保留原有结构并补充中文说明和新增参数校验 |

## 具体代码修改与功能说明

修改清单由本地代码与上游 `hjd1964/OnStep` 的 `release-4.24` 分支逐项比对得出。下面只展示本地实际新增或改进的代码，不重复粘贴未修改的上游实现

为了便于阅读，部分片段省略了无关上下文和重复分支，核心变量、判断条件与执行逻辑保持不变。每项说明依次标出修改文件、本地修改代码和修改带来的功能

### A 安全状态与命令入口

这一组修改先定义什么状态可以运动，再让所有自动命令服从同一套判断

#### 1 增加开机回零策略和电机保持配置

修改文件 `Config.h`

```cpp
#define HOME_REQUIRED_ON_BOOT          ON
#define HOME_REQUIRED_AFTER_LIMIT      ON
#define MOTOR_HOLD_ON_BOOT             ON
```

修改带来的功能

- `HOME_REQUIRED_ON_BOOT` 决定上电后是否必须先 Home 或 Set Home
- `HOME_REQUIRED_AFTER_LIMIT` 决定物理限位后是否重新建立位置基准
- `MOTOR_HOLD_ON_BOOT` 只负责上电使能驱动器，不会顺带开启 Tracking 或声明已经回零
- 三个选项彼此独立，可以按设备结构选择安全策略

#### 2 将位置可信状态从运动状态中解耦

修改文件 `OnStep.ino`

```cpp
enum GotoAbortState {
  GOTO_ABORT_NONE,
  GOTO_ABORT_STOPPED,
  GOTO_ABORT_HARD_STOP,
  GOTO_ABORT_POSITION_LOST
};

GotoAbortState gotoAbortState = GOTO_ABORT_NONE;
bool gotoStartTrackingOnSuccess = false;
bool mountPositionTrusted = true;
bool positionRecoveryRequired = false;
```

新增统一的状态操作函数

```cpp
bool positionReady() {
  return mountPositionTrusted && !positionRecoveryRequired;
}

bool positionHomeReturnOnly() {
  return mountPositionTrusted && positionRecoveryRequired;
}

void requireCoordinateHomeRecovery() {
  mountPositionTrusted = true;
  positionRecoveryRequired = true;
  gotoStartTrackingOnSuccess = false;
}

void invalidatePositionReference() {
  mountPositionTrusted = false;
  positionRecoveryRequired = true;
  gotoStartTrackingOnSuccess = false;
}

void completePositionRecovery() {
  mountPositionTrusted = true;
  positionRecoveryRequired = false;
  gotoAbortState = GOTO_ABORT_NONE;
  gotoStartTrackingOnSuccess = false;
  clearPhysicalLimitState();
}
```

修改带来的功能

- 不再把停止运动、已经回零和位置可信混为同一个状态
- 可以区分正常使用、仅允许返回坐标 Home、必须重新建立位置基准三种情况
- GOTO、Tracking、Park、自动回零和 Set Home 共用同一套状态来源
- 限位或故障后不会因为某个运动变量恢复正常就误解锁自动动作

#### 3 开机保持电机但不建立虚假坐标

修改文件 `OnStep.ino`

```cpp
#if HOME_REQUIRED_ON_BOOT == ON
  #if MOUNT_TYPE != ALTAZM
    #if HOME_SENSE == OFF
      requireCoordinateHomeRecovery();
    #else
      invalidatePositionReference();
    #endif

    gotoAbortState = GOTO_ABORT_NONE;
    trackingState = TrackingNone;
    lastTrackingState = TrackingNone;
    abortTrackingState = TrackingNone;
    safetyLimitsOn = false;
  #endif
#endif

#if MOTOR_HOLD_ON_BOOT == ON
  #if MOUNT_TYPE != ALTAZM
    enableStepperDrivers();
    axis1DriverTrackingMode(false);
    axis2DriverTrackingMode(false);
  #endif
#endif
```

修改带来的功能

- 有 Home 传感器时，上电位置直接标记为不可信
- 没有 Home 传感器时，保留原始步数坐标，但只允许先返回 Home 或执行 Set Home
- 电机使用跟踪细分和跟踪电流形成保持力矩
- 上电不会发出跟踪脉冲，也不会因为电机已使能就允许 GOTO

#### 4 统一拦截未恢复状态下的 GOTO 和 Sync

修改文件 `Goto.ino`

```cpp
CommandErrors validateGoto() {
  if (parkStatus != NotParked)                 return CE_SLEW_ERR_IN_PARK;
  if (!axis1Enabled)                           return CE_SLEW_ERR_IN_STANDBY;
  if (trackingSyncInProgress())                return CE_MOUNT_IN_MOTION;
  if (trackingState == TrackingMoveTo)         return CE_GOTO_ERR_GOTO;
  if (guideDirAxis1 || guideDirAxis2)          return CE_MOUNT_IN_MOTION;
  if (faultAxis1 || faultAxis2)                return CE_SLEW_ERR_HARDWARE_FAULT;
  if (!positionReady())                        return CE_SLEW_ERR_IN_STANDBY;
  return CE_NONE;
}
```

`:MS#`、Sync 和其他 GOTO 入口原本就会经过 `validateGoto()`。因此新增的一行位置检查能够覆盖全部自动指向入口，不需要在每条 LX200 命令中重复实现

修改带来的功能

- `:MS#`、同步指令和其他 GOTO 入口都无法绕过位置可信检查
- 位置未恢复时返回 standby，不会让 N.I.N.A 或 ASCOM 真正启动电机
- 上游原有的地平线、Axis1、Axis2、中天和墩侧校验仍然保留
- 错误码仍沿用 OnStep 4.24 的 LX200 回复格式

#### 5 Park 位置也必须建立在可信坐标上

修改文件 `Park.ino`

```cpp
CommandErrors setPark() {
  if (parkStatus == ParkFailed)         return CE_PARK_FAILED;
  if (parkStatus == Parked)             return CE_PARKED;
  if (isSlewing())                      return CE_MOUNT_IN_MOTION;
  if (faultAxis1 || faultAxis2)         return CE_SLEW_ERR_HARDWARE_FAULT;
  if (!positionReady())                 return CE_SLEW_ERR_IN_STANDBY;

  // 原版保存 Park 位置的逻辑继续执行
}
```

修改带来的功能

- 未回零或位置已经失信时不能保存错误的 Park 坐标
- 避免下一次启动从错误 Park 数据恢复机械位置

#### 6 Tracking 被拦截时立即回复客户端

修改文件 `Command.ino`

```cpp
if (command[0] == 'T' && parameter[0] == 0) {
  const bool trackingBlockedUntilRecovery =
    command[1] == 'e' && !positionReady();

  if (trackingBlockedUntilRecovery) {
    commandError = CE_SLEW_ERR_IN_STANDBY;
  } else {
    // 原版 Tracking 命令继续处理
  }
}
```

修改带来的功能

- 只拦截 `:Te#` 开启跟踪，不影响 `:Td#` 停止跟踪
- 位置不可信时不会进入恒星跟踪
- 保留命令处理器的布尔回复，客户端会立即收到 `0`
- 修复旧实现提前退出并抑制回复后 N.I.N.A 或 ASCOM 等待超时的问题

#### 7 修复首次连接误报已经回零

修改文件 `Command.ino`

```cpp
if (atHome && positionReady()) reply[i++] = 'H';
```

修改带来的功能

- 上电后即使内部 `atHome` 仍保留启动值，也不会向客户端报告可信 Home
- 只有自动回零成功或 Set Home 完成后，`:GU#` 才返回 `H`
- 客户端不会因为首次连接的错误状态直接放行自动 GOTO

### B 物理限位与手动脱困

这一组修改负责识别危险方向、停止撞击并保留反向脱困能力

#### 8 保留手动移动并在 Guide 层限制危险方向

修改文件 `Guide.ino`

Axis1 的底层限制

```cpp
bool escapingPhysicalLimitAxis1 = false;

#if LIMIT_SENSE != OFF
  if (direction == 'e' && Axis1_LimitLock == 1)
    return CE_SLEW_ERR_OUTSIDE_LIMITS;

  if (direction == 'w' && Axis1_LimitLock == -1)
    return CE_SLEW_ERR_OUTSIDE_LIMITS;

  escapingPhysicalLimitAxis1 =
    generalError == ERR_LIMIT_SENSE &&
    ((direction == 'e' && Axis1_LimitLock == -1) ||
     (direction == 'w' && Axis1_LimitLock == 1));
#endif
```

Axis2 使用相同方式处理 North 和 South

```cpp
bool escapingPhysicalLimitAxis2 = false;

#if LIMIT_SENSE != OFF
  if (direction == 'n' && Axis2_LimitLock == 1)
    return CE_SLEW_ERR_OUTSIDE_LIMITS;

  if (direction == 's' && Axis2_LimitLock == -1)
    return CE_SLEW_ERR_OUTSIDE_LIMITS;

  escapingPhysicalLimitAxis2 =
    generalError == ERR_LIMIT_SENSE &&
    ((direction == 'n' && Axis2_LimitLock == -1) ||
     (direction == 's' && Axis2_LimitLock == 1));
#endif
```

修改带来的功能

- 未回零不会锁死 `:Me#`、`:Mw#`、`:Mn#` 和 `:Ms#`
- 触发限位后只拒绝继续撞击的一侧
- 反方向手动移动可以绕过 `ERR_LIMIT_SENSE` 完成脱困
- 限制放在 Guide 底层，串口命令、ST4 和其他调用入口都不能绕过

#### 9 在主循环中记录限位危险方向

修改文件 `OnStep.ino`

```cpp
if (limit_reading == LIMIT_SENSE_STATE) {
  lastLimitTriggerTime = currentTime;

  if (isHoming()) {
    Axis1_LimitLock = 0;
    Axis2_LimitLock = 0;
    return;
  }

  delay(2);
  if (digitalRead(LimitPin) == LIMIT_SENSE_STATE) {
    int currentMotionDir1 = 0;
    int currentMotionDir2 = 0;

    if (guideDirAxis1 == 'e') currentMotionDir1 = 1;
    else if (guideDirAxis1 == 'w') currentMotionDir1 = -1;

    if (guideDirAxis2 == 'n') currentMotionDir2 = 1;
    else if (guideDirAxis2 == 's') currentMotionDir2 = -1;

    if (trackingState == TrackingMoveTo) {
      if (targetAxis1.part.m < posAxis1) currentMotionDir1 = 1;
      else if (targetAxis1.part.m > posAxis1) currentMotionDir1 = -1;

      if (targetAxis2.part.m > posAxis2) currentMotionDir2 = 1;
      else if (targetAxis2.part.m < posAxis2) currentMotionDir2 = -1;
    }

    if (Axis1_LimitLock == 0) {
      if (currentMotionDir1 != 0 &&
          trackingState == TrackingMoveTo) {
        Axis1_LimitLock = currentMotionDir1;
      } else {
        long threshold = 500L;
        if (posAxis1 > threshold) Axis1_LimitLock = -1;
        else if (posAxis1 < -threshold) Axis1_LimitLock = 1;
        else if (currentMotionDir1 != 0)
          Axis1_LimitLock = currentMotionDir1;
      }
    }

    if (Axis2_LimitLock == 0) {
      if (currentMotionDir2 != 0 &&
          trackingState == TrackingMoveTo) {
        Axis2_LimitLock = currentMotionDir2;
      } else {
        long threshold = 500L;
        if (posAxis2 > threshold) Axis2_LimitLock = 1;
        else if (posAxis2 < -threshold) Axis2_LimitLock = -1;
        else if (currentMotionDir2 != 0)
          Axis2_LimitLock = currentMotionDir2;
      }
    }

    const bool axis1MovingIntoLimit =
      Axis1_LimitLock != 0 && currentMotionDir1 == Axis1_LimitLock;

    const bool axis2MovingIntoLimit =
      Axis2_LimitLock != 0 && currentMotionDir2 == Axis2_LimitLock;

    const bool hasEscapeMotion =
      currentMotionDir1 != 0 || currentMotionDir2 != 0;

    const bool isEscaping =
      hasEscapeMotion && !axis1MovingIntoLimit && !axis2MovingIntoLimit;

    if (!isEscaping) {
      generalError = ERR_LIMIT_SENSE;
      stopGuideAxis1();
      stopGuideAxis2();
      stopSlewingAndTracking(SS_LIMIT_PHYSICAL);
    }
  }
}
```

限位释放后的清锁逻辑

```cpp
if (currentTime - lastLimitTriggerTime > 500) {
  if (guideDirAxis1 == 0 && trackingState != TrackingMoveTo)
    Axis1_LimitLock = 0;

  if (guideDirAxis2 == 0 && trackingState != TrackingMoveTo)
    Axis2_LimitLock = 0;
}
```

修改带来的功能

- GOTO 和手动移动都能记录真实运动方向
- 静止触发时会结合轴位置推断危险侧，减少按键松开后丢失方向的问题
- 双轴中只要有一轴仍在撞向限位就不会把整体误判为正在脱困
- 限位释放并停止 500 毫秒后自动清锁

### C 自动回零与位置恢复

这一组修改把自动回零扩展为可配置的三阶段流程，并明确成功与失败的边界

#### 10 ST4 East 和 West 长按 3 秒启动回零

修改文件 `Guide.ino`

```cpp
static bool homingLockout = false;

if (homingLockout) {
  if (!st4e.isDown() && !st4w.isDown() &&
      !st4n.isDown() && !st4s.isDown()) {
    homingLockout = false;
  }
  return;
}

if (trackingState != TrackingMoveTo && !waitingHome) {
  if (st4e.isDown() && st4w.isDown()) {
    if (st4e.timeDown() > 3000 && st4w.timeDown() > 3000) {
      homingLockout = true;
      soundBeep();
      altModeA = false;
      stopGuideAxis1();
      stopGuideAxis2();
      stopSlewingAndTracking(SS_ALL_FAST);
      goHome(true);
      return;
    }
  }
}
```

修改带来的功能

- 不连接电脑也能通过实体按键启动 Find Home
- 保留上游原有的 East 和 West 长按 2 秒 Alt Mode
- 3 秒触发时主动清除 Alt Mode，避免组合键状态污染回零
- 回零开始后屏蔽残留按压，全部松手后才恢复 ST4 输入

#### 11 将自动回零扩展为三阶段状态机

修改文件 `Home.ino`

原始 OnStep 4.24 的状态机只有快速搜索、慢速精找和完成。当前版本增加 `FH_IDLE2` 与 `FH_OFFSET`

```cpp
enum findHomeModes {
  FH_OFF,
  FH_FAST,
  FH_IDLE,
  FH_SLOW,
  FH_IDLE2,
  FH_OFFSET,
  FH_DONE
};
```

第一和第二阶段的速度与超时改为配置驱动

```cpp
double secPerDeg = 3600.0 / (double)guideRates[HOME_FAST_RATE];
findHomeTimeout = millis() +
  (unsigned long)(secPerDeg * 360.0 * 1000.0);

e = startGuideAxis1(a1, HOME_FAST_RATE, 0, false);
if (e == CE_NONE)
  e = startGuideAxis2(a2, HOME_FAST_RATE, 0, false, true);
```

```cpp
double secPerDeg = 3600.0 / (double)guideRates[HOME_SLOW_RATE];
findHomeTimeout = millis() +
  (unsigned long)(secPerDeg * 6.0 * 1000.0);

e = startGuideAxis1(a1, HOME_SLOW_RATE, 0, false);
if (e == CE_NONE)
  e = startGuideAxis2(a2, HOME_SLOW_RATE, 0, false, true);
```

第三阶段按角度换算运行时间

```cpp
double secPerDeg = 3600.0 / (double)guideRates[HOME_OFFSET_RATE];

if (HOME_OFFSET_AXIS1 != 0.0 && AXIS2_TANGENT_ARM == OFF) {
  char dir1 = HOME_OFFSET_AXIS1 > 0 ? 'e' : 'w';
  unsigned long duration1 =
    (unsigned long)(fabs(HOME_OFFSET_AXIS1) * secPerDeg * 1000.0);

  e1 = startGuideAxis1(dir1, HOME_OFFSET_RATE, 0, false);
  if (e1 == CE_NONE) offsetTimeoutAxis1 = millis() + duration1;
}

if (HOME_OFFSET_AXIS2 != 0.0) {
  char dir2 = HOME_OFFSET_AXIS2 > 0 ? 'n' : 's';
  unsigned long duration2 =
    (unsigned long)(fabs(HOME_OFFSET_AXIS2) * secPerDeg * 1000.0);

  e2 = startGuideAxis2(dir2, HOME_OFFSET_RATE, 0, false, true);
  if (e2 == CE_NONE) offsetTimeoutAxis2 = millis() + duration2;
}
```

修改带来的功能

- 快速搜索、慢速精找和偏置速度都能在 `Config.h` 调整
- 改变搜索速度后，超时保护仍对应固定的角度范围
- Home 开关安装位置不必与最终机械零位完全重合
- 双轴偏置角度可以分别设置正负方向
- 双轴分别到时停止，全部停稳后才把新位置设为真正零位

#### 12 回零失败不再进入成功状态

修改文件 `Home.ino`

第一或第二阶段超时和异常停止时

```cpp
if ((long)(millis() - findHomeTimeout) > 0L ||
    (guideDirAxis1 == 0 && guideDirAxis2 == 0)) {

  if ((long)(millis() - findHomeTimeout) > 0L)
    generalError = ERR_LIMIT_SENSE;

  safetyLimitsOn = true;
  invalidatePositionReference();
  gotoAbortState = GOTO_ABORT_NONE;
  findHomeMode = FH_OFF;
}
```

第三阶段启动失败时

```cpp
if (e1 != CE_NONE || e2 != CE_NONE) {
  findHomeMode = FH_OFF;
  safetyLimitsOn = true;
  generalError = ERR_LIMIT_SENSE;
  stopSlewingAndTracking(SS_ALL_FAST);
  return;
}
```

只有 `FH_DONE` 才恢复位置

```cpp
if (findHomeMode == FH_DONE &&
    guideDirAxis1 == 0 && guideDirAxis2 == 0) {

  findHomeMode = FH_OFF;
  initStartPosition();
  atHome = true;
  completePositionRecovery();
  safetyLimitsOn = true;
  abortGoto = 0;
  generalError = ERR_NONE;
}
```

修改带来的功能

- 传感器没有触发、搜索超时或电机没有成功启动时不会误报 Home 完成
- 回零失败后 GOTO 和 Tracking 继续保持锁定
- 只有双轴完整走完三阶段并停稳后才重建坐标

#### 13 Set Home 成为明确的人工恢复入口

修改文件 `Home.ino`

```cpp
CommandErrors setHome() {
  if (isSlewing()) return CE_MOUNT_IN_MOTION;

  reactivateBacklashComp();
  initStartupValues();
  initStartPosition();
  safetyLimitsOn = true;
  StepperModeTrackingInit();

  // 原版 PEC 与 Park 状态处理继续执行

  completePositionRecovery();
  abortGoto = 0;
  generalError = ERR_NONE;
  return CE_NONE;
}
```

修改带来的功能

- 用户把赤道仪手动放回定义的机械零位后，可以用 Set Home 恢复位置可信状态
- 有无 Home 传感器都使用相同的人工确认语义
- 清理上一次限位、故障和 GOTO 中断留下的恢复状态
- Set Home 不是自动寻找零位，执行前必须由用户确认机械位置正确

### D GOTO 与 Tracking 收尾

这一组修改解决 GOTO 中止后的状态恢复和错误自动 Tracking

#### 14 对 GOTO 停止原因进行分类

修改文件 `OnStep.ino`

```cpp
if (ss == SS_LIMIT_HARD) {
  invalidatePositionReference();
  safetyLimitsOn = false;

  if (trackingState == TrackingMoveTo)
    gotoAbortState = GOTO_ABORT_POSITION_LOST;
}

if (ss == SS_LIMIT_PHYSICAL) {
  gotoStartTrackingOnSuccess = false;

#if HOME_REQUIRED_AFTER_LIMIT == ON
  #if HOME_SENSE == OFF
    requireCoordinateHomeRecovery();
  #else
    invalidatePositionReference();
  #endif

  safetyLimitsOn = false;
  if (trackingState == TrackingMoveTo)
    gotoAbortState = GOTO_ABORT_POSITION_LOST;
#else
  if (trackingState == TrackingMoveTo)
    gotoAbortState = GOTO_ABORT_HARD_STOP;
#endif
}

if (trackingState == TrackingMoveTo) {
  gotoStartTrackingOnSuccess = false;

  if (ss != SS_ALL_FAST && gotoAbortState == GOTO_ABORT_NONE)
    gotoAbortState = GOTO_ABORT_STOPPED;

  if (!abortGoto) abortGoto = StartAbortGoto;
}
```

修改带来的功能

- 驱动器硬故障直接判定为可能丢步
- 物理限位是否强制回零由 `HOME_REQUIRED_AFTER_LIMIT` 控制
- 普通软件范围停止不会覆盖更严重的位置丢失状态
- 任何 GOTO 中止都会取消本次正常到达后的自动 Tracking 请求

#### 15 GOTO 完成时不再把安全中断当作正常到达

修改文件 `Goto.ino` 和 `MoveTo.ino`

启动 GOTO 前只记录一次正常到达后的 Tracking 请求

```cpp
const bool requestTrackingAfterSuccess =
  trackingState == TrackingNone &&
  timeWasSet && dateWasSet &&
  positionReady() &&
  parkStatus == NotParked &&
  !isHoming();

CommandErrors result =
  goTo(Axis1, Axis2, Axis1Alt, Axis2Alt, thisPierSide);

if (result == CE_NONE)
  gotoStartTrackingOnSuccess = requestTrackingAfterSuccess;
```

GOTO 收尾时按中断类型分别处理

```cpp
if (completedGotoState == GOTO_ABORT_POSITION_LOST ||
    !positionReady()) {

  trackingState = TrackingNone;
  lastTrackingState = TrackingNone;
  if (generalError == ERR_NONE) generalError = ERR_LIMIT_SENSE;

} else if (completedGotoState == GOTO_ABORT_HARD_STOP) {

  trackingState = TrackingNone;
  lastTrackingState = TrackingNone;

} else {

  trackingState = lastTrackingState;
  lastTrackingState = TrackingNone;

  if (completedGotoState == GOTO_ABORT_NONE && startTracking)
    trackingState = TrackingSidereal;

  if (completedGotoState == GOTO_ABORT_NONE &&
      trackingState == TrackingSidereal) {
    trackingSyncSeconds = 5;
  }
}

gotoAbortState = GOTO_ABORT_NONE;
gotoStartTrackingOnSuccess = false;
```

修改带来的功能

- 正常完成、普通停止、物理停止和位置丢失有不同的收尾行为
- 安全中断后不会输出正常 GOTO done 流程
- GOTO 被拦截或急停后不会出现幽灵 Tracking
- 上游原有的正常到达后 5 秒 Tracking 同步窗口仍被保留

### E MaxESP3 驱动与引脚适配

这一组修改处理共享细分引脚、双轴同步切换和当前控制板接线

#### 16 标记 MaxESP3 双轴共享模式引脚

修改文件 `src/pinmaps/Pins.MaxESP3.h`

```cpp
#define Axis1_M0 13
#define Axis1_M1 14

#define Axis2_M0 13
#define Axis2_M1 14

#define AXIS12_DRIVER_MODE_PINS_SHARED
```

修改文件 `Validate.h`

```cpp
#if defined(AXIS12_DRIVER_MODE_PINS_SHARED) && \
    (AXIS1_DRIVER_MODEL == TMC2209 || AXIS2_DRIVER_MODEL == TMC2209)

  #if AXIS1_DRIVER_MODEL != TMC2209 || AXIS2_DRIVER_MODEL != TMC2209
    #error "shared M0/M1 pins require TMC2209 on both axes"
  #endif

  #if AXIS1_DRIVER_MICROSTEPS != AXIS2_DRIVER_MICROSTEPS
    #error "shared M0/M1 pins require equal tracking microsteps"
  #endif

  #if AXIS1_DRIVER_MICROSTEPS_GOTO != AXIS2_DRIVER_MICROSTEPS_GOTO
    #error "shared M0/M1 pins require equal Goto microsteps"
  #endif

  #if MODE_SWITCH_BEFORE_SLEW != OFF
    #error "shared M0/M1 pins require on-the-fly mode switching"
  #endif

  #define AXIS12_TMC2209_MODE_SHARED
#endif
```

修改带来的功能

- 编译阶段就能发现双轴驱动器和细分配置不一致
- 防止只修改一个轴后生成可以编译但运动比例错误的固件
- TMC5160 等 SPI 驱动仍通过各自 CS 独立控制，不会误用 TMC2209 共享逻辑

#### 17 双轴以同一个时机切换 TMC2209 细分

修改文件 `Timer.ino` 和 `StepMode.ino`

两个轴共用同一个 GOTO 模式判断

```cpp
gotoRateAxis1 =
  thisTimerRateAxis1 < AXIS1_DRIVER_SWITCH_RATE ||
  thisTimerRateAxis2 < AXIS2_DRIVER_SWITCH_RATE;

gotoRateAxis2 = gotoRateAxis1;
```

切换前等待双轴都到达粗细分可以表示的位置

```cpp
bool axis1Ready =
  (!inbacklashAxis1 && posAxis1 == (long)targetAxis1.part.m) ||
  ((posAxis1 + blAxis1) % axis1StepsGoto == 0);

bool axis2Ready =
  (!inbacklashAxis2 && posAxis2 == (long)targetAxis2.part.m) ||
  ((posAxis2 + blAxis2) % axis2StepsGoto == 0);

if (!axis1Ready || !axis2Ready) return;
```

清除双轴 STEP 后一次更新模式和软件步距

```cpp
a1CLEAR;
a2CLEAR;

if (gotoRateAxis1) {
  axis1DriverGotoFast();
  gotoModeAxis1 = true;
  gotoModeAxis2 = true;
} else {
  axis1DriverTrackingFast();
  gotoModeAxis1 = false;
  gotoModeAxis2 = false;
}
```

`StepMode.ino` 中共享模式会同时更新两个轴的软件步距

```cpp
#ifdef AXIS12_TMC2209_MODE_SHARED
  stepAxis1 = axis1StepsGoto;
  stepAxis2 = axis2StepsGoto;
#endif
```

修改带来的功能

- 任一轴需要高速粗细分时，两个硬件驱动同时切换
- 一个轴先减速时不会单独改变另一个轴的细分
- 硬件模式与双轴软件坐标比例保持一致
- 恢复 MaxESP3 独立 TMC2209 的 32 细分 GOTO 能力

#### 18 修改 MaxESP3 引脚以匹配当前控制板

修改文件 `src/pinmaps/Pins.MaxESP3.h`

```cpp
#define Aux5           25
#define Aux6           15
#define Aux7           39

#define Axis1_EN        4
#define Axis1_STEP     18
#define Axis1_DIR      19
#define Axis1_HOME   Aux5

#define Axis2_EN   SHARED
#define Axis2_STEP     27
#define Axis2_DIR      26
#define Axis2_HOME   Aux6

#define LimitPin     Aux7
#define PpsPin         36
```

修改带来的功能

- Axis1 Home 从上游的 I2C 复用脚移到 GPIO25
- Axis2 Home 从上游的 I2C 复用脚移到 GPIO15
- GPIO21 和 GPIO22 可以保留给 DS3231 的 SDA 与 SCL
- Axis1 Dir 改到 GPIO19，Axis1 Enable 改到 GPIO4
- PPS 与 Limit 使用独立输入
- 不使用的旋转器和调焦器引脚被关闭，避免与当前赤道仪接线冲突

## 运行逻辑总览

前面的代码修改共同形成一条完整的安全链路

```text
上电
  ↓
电机进入保持状态，Tracking 保持关闭
  ↓
位置未确认，GOTO、Sync、Park 和 Tracking 暂时锁定
  ↓
手动移动仍可使用
  ↓
自动 Home 或人工确认后的 Set Home
  ↓
位置恢复可信，开放自动动作
```

如果运行中触发物理限位或驱动故障，固件会停止运动并分类记录中止原因。物理限位允许向安全方向手动脱困。需要重新建立位置基准时，只有 Home 或 Set Home 能解除自动动作锁

自动回零依次执行快速搜索、慢速精找和零位偏置。当前默认速度档位为 9、7、8，双轴偏置分别为 -1.5 度和 1 度。任一阶段失败都不会进入完成状态

MaxESP3 使用独立模式 TMC2209 时，双轴共享 M0 和 M1。当前代码要求双轴细分一致，并在同一时机切换硬件模式和软件步距。仓库默认驱动仍为 `TMC5160_QUIET`，TMC2209 支持需要按实际硬件启用

## 当前默认硬件配置

这份仓库已经带有一套具体设备配置，不是上游的空白模板

| 项目 | 当前值 |
| --- | --- |
| 主控和引脚映射 | MaxESP3 |
| 架台类型 | GEM |
| 时间源 | DS3231 |
| 双轴驱动 | TMC5160 Quiet |
| 跟踪细分 | 64 |
| GOTO 细分 | 32 |
| 期望 GOTO 速度 | 6 度每秒 |
| Home 传感器 | 上拉输入 |
| Limit 传感器 | 上拉输入 |
| ST4 手柄 | 启用 |
| PPS | 启用 |

### 当前 MaxESP3 引脚

本项目修改过上游 MaxESP3 引脚定义。接线时应以 `src/pinmaps/Pins.MaxESP3.h` 为准，不能直接套用原始 OnStep 4.24 的 MaxESP3 接线图

| 功能 | GPIO |
| --- | ---: |
| Axis1 Enable | 4 |
| Axis1 Step | 18 |
| Axis1 Dir | 19 |
| Axis1 Home | 25 |
| Axis2 Enable | 与 Axis1 共用 |
| Axis2 Step | 27 |
| Axis2 Dir | 26 |
| Axis2 Home | 15 |
| Limit | 39 |
| PPS | 36 |
| I2C SDA | 21 |
| I2C SCL | 22 |
| TMC SPI MISO | 2 |
| Axis1 CS | 23 |
| Axis2 CS | 5 |
| ST4 West | 34 |
| ST4 South | 32 |
| ST4 North | 33 |
| ST4 East | 35 |

旋转器和两个调焦器的默认步进引脚已关闭，为当前赤道仪接线让出 GPIO

## 编译前需要修改的内容

不要直接把默认固件刷进另一台赤道仪

至少检查这些参数

| 文件 | 需要确认的内容 |
| --- | --- |
| `Config.h` | 主板、驱动器、细分、每度步数、电流、方向和速度 |
| `Config.h` | Home 和 Limit 开关类型以及有效电平 |
| `Config.h` | 双轴偏置角度和三个回零速度 |
| `Config.h` | Axis1 和 Axis2 软件范围 |
| `src/pinmaps/Pins.MaxESP3.h` | 当前 PCB 的真实接线 |
| `src/pinmaps/Validate.MaxESP3.h` | 修改引脚后对应的资源占用校验 |

当前 `AXIS1_LIMIT_MIN` 和 `AXIS1_LIMIT_MAX` 是 `-180` 与 `180`。这只是现有设备的配置，不代表任何赤道仪都能安全旋转到这个范围。请根据三脚架、镜筒、线缆和机械结构重新设定

## 编译与上传

1. 保持工程目录名为 `OnStep`
2. 使用支持原始 OnStep 4.24 的 Arduino 开发环境打开 `OnStep.ino`
3. 根据自己的硬件完成 `Config.h` 和引脚检查
4. 编译并认真处理 `Validate.h` 给出的错误
5. 断开镜筒负载或在可随时断电的条件下完成第一次台架测试
6. 验证电机方向、Home 极性、Limit 极性和 ST4 方向后再装载设备

校验报错通常意味着细分组合或引脚占用存在冲突，不建议通过删除校验代码绕过

## 推荐使用流程

```text
上电
  ↓
确认双轴已有保持力矩
  ↓
确认回零路径没有线缆和机械干涉
  ↓
通过客户端 Find Home
或长按 ST4 East 和 West 3 秒
  ↓
等待三阶段回零完成
  ↓
确认状态中出现可信 Home
  ↓
开始 GOTO、中心定位和跟踪
```

触发限位后先向相反方向手动脱困，再执行 Find Home。只有在人工确认赤道仪已经放到定义的机械零位时才使用 Set Home

## 使用边界

- 本项目面向当前 MaxESP3 GEM 谐波赤道仪，不是所有 OnStep 设备的通用替代固件
- 步进系统仍是开环控制，堵转、断电和机械打滑后必须重新建立位置基准
- 零位偏置按时间换算运动角度，修改速度、细分或机械参数后需要重新校准
- 单个 Limit 输入需要结合运动方向和当前位置推断危险方向，第一次测试必须低速进行
- Home 期间必须保证传感器可靠并留有足够机械余量
- 软件限位不能替代合理的结构设计、线缆管理和物理急停

## 协议兼容

固件继续使用 OnStep 的 LX200 派生命令集，可以配合 OnStep App、ASCOM、N.I.N.A、Stellarium、SkySafari、INDI 和其他兼容客户端使用

客户端看到 standby 或 Tracking 开启失败时，先检查是否已经完成 Home 或 Set Home，再检查 Park、驱动故障、物理限位和软件运动范围

## 致谢与许可

感谢 Howard Dutton 和 OnStep 社区长期维护这个开放的望远镜控制项目

本项目是 OnStep 4.24 的衍生版本，继续遵循 GNU General Public License。原始项目版权和许可说明见 [LICENSE.txt](./LICENSE.txt)
