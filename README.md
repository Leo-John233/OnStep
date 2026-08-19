# OnStep Telescope Controller — Custom

基于 [hjd1964/OnStep](https://github.com/hjd1964/OnStep) `release-4.24` 开发的自定义 OnStep 固件。

本分支主要用于自制谐波赤道仪及 MaxESP3 控制器，在原始 OnStep 4.24 基础上针对实际硬件和使用需求进行了修改。

> [!IMPORTANT]
> 本项目是 OnStep 的非官方修改版本。
>
> OnStep 原项目及核心固件由 **Howard Dutton** 开发和维护。

## 分支说明

| 分支 | 用途 |
| --- | --- |
| `release-4.24` | OnStep 4.24 上游基线，用于同步和代码比较 |
| `release-4.24-custom` | 当前自定义稳定版本 |
| `release-4.24-custom-dev` | 自定义开发和测试版本 |

一般使用建议选择：

`release-4.24-custom`

开发中的功能和未经完整验证的修改位于：

`release-4.24-custom-dev`

## 主要修改

相对于原始 OnStep 4.24，本项目主要进行了以下调整：

- MaxESP3 硬件适配
- TMC2209 驱动及细分逻辑调整
- RA / DEC 控制逻辑调整
- RA / DEC 功能解耦
- Home 回零逻辑修改
- 物理限位逻辑调整
- GOTO 相关问题修复
- ZWO 控制设备兼容性调整
- 独立回零按键支持
- Config.h 配置调整
- 中文注释及代码整理

具体修改内容以 Git 提交记录为准。

## Upstream

原始项目：

[hjd1964/OnStep](https://github.com/hjd1964/OnStep)

基础版本：

`release-4.24`

原作者：

**Howard Dutton**

## What is OnStep?

OnStep is a computerized telescope GOTO controller based on Teensy or Arduino control of stepper motors.

It supports equatorial mounts such as GEM and Fork mounts, as well as Alt-Az mounts including Dobsonians.

OnStep supports several communication methods including USB, Bluetooth, Wi-Fi and Ethernet, depending on the controller configuration.

It is compatible with the LX200 protocol and can be used with astronomy software including SkySafari, Stellarium, ASCOM and INDI compatible applications.

For complete documentation, hardware designs and configuration information, please refer to the original OnStep project.

## Documentation

- [Official OnStep Repository](https://github.com/hjd1964/OnStep)
- [OnStep Wiki](https://groups.io/g/onstep/wiki/home)
- [OnStep Group](https://groups.io/g/onstep/)

## License

OnStep is open-source software licensed under the GNU General Public License.

This modified version continues to be distributed under the applicable GPL license.

See [LICENSE.txt](./LICENSE.txt).

## Author

Original OnStep Author:

**Howard Dutton**

Custom modifications:

**Leo-John233 and project contributors**

完整修改记录请参阅本仓库 Git History。

---

## 📝 最近代码修改

<!-- RECENT_CHANGES:START -->

最近 **7 天**本仓库共有 **56** 次提交

<!-- RECENT_CHANGES:END -->

## 🟩 Repository Activity
