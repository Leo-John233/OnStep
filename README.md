OnStep Telescope Controller
===========================
# Important Note

THERE ARE SEVERAL GITHUB BRANCHES OF ONSTEP:
* The **RELEASE BRANCHES** are well tested and what most should use.  Usually the newest (highest revision) RELEASE is recommended.  No new features are added and only bug fixes where necessary and safe.
* Tne **BETA BRANCH**, if present, is a "snap-shot" of the MASTER where we have reached a point of apparent stability.  This provides access to most new features for adventurous users.
* The **MASTER BRANCH** is the most up to date OnStep version; where new features are added.  It is the least well tested branch and should only be user by experienced users willing to test for and report bugs.

# What is OnStep?
OnStep is a computerized telescope goto controller, based on Teensy or
Arduino control of stepper motors.

It supports Equatorial Mounts (GEM, Fork, etc.) as well as Alt-Az mounts
(including Dobsonians, and the like.)

OnStep was designed, from the beginning, as a more or less general purpose
system and provisions were made in the firmware to allow for use on a variety
of mounts.

# Features
OnStep supports a wide variety of connection options.  Either two or three serial
"command channels" can be utilized. One of the these is normally devoted to a USB
connection and for the other(s) choose from the following:

* Bluetooth
* ESP8266 WiFi
* Arduino M0/Ethernet Shield
* Even another USB port or RS232 serial isn't very difficult to add.

Other software in the OnStep ecosystem include:

* an [ASCOM](http://ascom-standards.org/) driver (with IP and Serial support),
* an Android App useable over WiFi or Bluetooth equipped Phones/Tablets
  (version 2.3.3 or later),
* a "built-in" website (on the Ethernet and/or WiFi device),
* a full planetarium program that controls all features ([Sky Planetarium](http://stellarjourney.com/index.php?r=site/software_sky)).

OnStep is compatible with the LX200 protocol. This means it can be controlled
from other planetarium software, like: Sky Safari, CdC (even without ASCOM),
Stellarium, etc.

There are also [INDI](http://www.indilib.org/about.html) drivers so it can be used from Linux, with CdC or KStars.

# Documentation
Detailed documentation, including the full set of features, detailed designs for
PCBs, instructions on how to build a controller, how to configure the firmware
for your particular mount, can all be found the [OnStep Group Wiki](https://groups.io/g/onstep/wiki/home).

# Change Log
All the changes are tracking in git, and a detailed list can be accessed using the
following git command:
 
git log --date=short --pretty=format:"%h %ad %<(20)%an %<(150,trunc)%s"

# Support
Questions and discussion should be on the mailing list (also accessible via the
web) at the [OnStep Group](https://groups.io/g/onstep/).

# License
OnStep is open source free software, licensed under the GPL.

See [LICENSE.txt](./LICENSE.txt) file.

# Author
[Howard Dutton](http://www.stellarjourney.com)

## 📝 最近代码修改

<!-- RECENT_CHANGES:START -->
最近 **7 天**代码提交 **56** 次

| 日期 | 修改者 | 修改内容 | 范围 |
| :---: | :--- | :--- | :--- |
| 8/19 | **Leo‑John233** | [修改文件夹名称](https://github.com/Dcmdan/OnStep/commit/75c0c2bb4d5d87ee724aaa82cae0093fd734e269) `75c0c2b` | `OnStep4.24固件-哆啦A梦 + 基于OnStep4.24固件修改-哆啦A梦` · 8146 |
| 8/19 | **Leo‑John233** | [手控器原始固件](https://github.com/Dcmdan/OnStep/commit/7ca30320ad08d82e66b6d02372d8214bf415b5e1) `7ca3032` | `SmartHandController` · 41 |
| 8/19 | **Leo‑John233** | [OnStepX 最新固件](https://github.com/Dcmdan/OnStep/commit/761c088559b2fdcc6a26dc26de801b25e7eaec47) `761c088` | `OnStepX` · 91 |
| 8/19 | **Leo‑John233** | [OnStepX 最新固件](https://github.com/Dcmdan/OnStep/commit/c7ba9faa5a8c79745b1512ec68cdaf3c75b35140) `c7ba9fa` | `OnStepX` · 20 |
| 8/19 | **Leo·John** | [Delete 原始固件/OnStep4.24/readme.md](https://github.com/Dcmdan/OnStep/commit/3c300415be6bb191a87bf2fe08b7947cec41a1e8) `3c30041` | `OnStep4.24/readme.md` |
| 8/19 | **Leo‑John233** | [OnStep4.24原始固件](https://github.com/Dcmdan/OnStep/commit/13d73ddf697a3ee0a6091ae1173413f03393a319) `13d73dd` | `OnStep4.24` · 181 |
| 8/19 | **Leo‑John233** | [OnStep4.24原始固件上传](https://github.com/Dcmdan/OnStep/commit/4b9b0b9c1cc8a1b88d86ed611163af363281f2aa) `4b9b0b9` | `OnStep4.24` · 63 |
| 8/19 | **Leo·John** | [Add files via upload](https://github.com/Dcmdan/OnStep/commit/801e45aeaf8e61c46907f3f288e6e6ac870f1955) `801e45a` | `OnStep4.24` · 23 |
| 8/19 | **Leo‑John233** | [上传原始固件](https://github.com/Dcmdan/OnStep/commit/328625ac14c38dd761b05a97a0e351ac91466a19) `328625a` | `OnStep4.24/readme.md` |
| 8/19 | **Leo‑John233** | [整理项目，重新修改文件树](https://github.com/Dcmdan/OnStep/commit/5d674d52b16557316b0ec9029b3b45ea56355cad) `5d674d5` | `多个目录` · 26 |
| 8/19 | **Leo·John** | [Delete src directory](https://github.com/Dcmdan/OnStep/commit/6debbbde24169f4a189aee51507387f8e1535314) `6debbbd` | `src` · 108 |
| 8/19 | **Leo·John** | [Delete libraries directory](https://github.com/Dcmdan/OnStep/commit/4b3ca511ada4d29a0a26b099d115b6abe9d38f13) `4b3ca51` | `libraries` · 3805 |
| 8/19 | **Leo·John** | [Delete doc directory](https://github.com/Dcmdan/OnStep/commit/2eebc31a4c8e38f65334f8b16953b67ac718a690) `2eebc31` | `doc` · 4 |
| 8/19 | **Leo·John** | [Delete addons directory](https://github.com/Dcmdan/OnStep/commit/ed38e29ce53616969bf4f93495ad7e3c9c8ffdac) `ed38e29` | `addons` · 138 |
| 8/19 | **Leo·John** | [Delete 原始固件/readme.md](https://github.com/Dcmdan/OnStep/commit/c6078fbd130ac4f8b21cedade9b499cc91269fa8) `c6078fb` | `readme.md` |
| 8/19 | **Leo‑John233** | [Move SmartWebServer into 原始固件](https://github.com/Dcmdan/OnStep/commit/d3d3c369f952a7ffc8a511a96d07b563d4833f74) `d3d3c36` | `SmartWebServer` · 676 |
| 8/19 | **Leo·John** | [Create readme.md](https://github.com/Dcmdan/OnStep/commit/4a03a36acb39ddbf64c4641b75c80168d173d00b) `4a03a36` | `readme.md` |
| 8/19 | **Leo·John** | [Delete 原始固件](https://github.com/Dcmdan/OnStep/commit/77b3d70ac35a9318db06da1d5d7f92e515dc130b) `77b3d70` | `原始固件` |
| 8/19 | **Leo·John** | [Create 原始固件](https://github.com/Dcmdan/OnStep/commit/6367b0117dc07d2f6200b25cf5256d82d2075705) `6367b01` | `原始固件` |
| 8/19 | **Leo‑John233** | [Update OnStep4.24固件-哆啦A梦 from main](https://github.com/Dcmdan/OnStep/commit/0cec43fdd4e93e3dc2e47d876ed0ea8cdbcf9cd5) `0cec43f` | `OnStep4.24固件-哆啦A梦` · 4072 |
| 8/19 | **Leo‑John233** | [Add OnStep4.24 firmware folder](https://github.com/Dcmdan/OnStep/commit/445f5e8ca4282d1768d04f05e48106f979840dd5) `445f5e8` | `OnStep4.24固件-哆啦A梦/.gitkeep` |
| 8/19 | **Leo‑John233** | [测试worksapce](https://github.com/Dcmdan/OnStep/commit/0cc68d2b9c76ed3ab583ae4ccfef2ee80f907845) `0cc68d2` | `OnStep4.24固件-哆啦A梦/Config.h` |
| 8/19 | **Leo‑John233** | [测试worksapce](https://github.com/Dcmdan/OnStep/commit/88c316e5b66eea8b44c69e7199759d208fb208f5) `88c316e` | `Config.h` |
| 8/19 | **Leo‑John233** | [测试合并](https://github.com/Dcmdan/OnStep/commit/e2479ea53b992eb5af53396734863b8e643aa9e9) `e2479ea` | `OnStep4.24固件-哆啦A梦/Config.h` |
| 8/19 | **Leo‑John233** | [测试合并](https://github.com/Dcmdan/OnStep/commit/d3f239041f1654c95f864574dd44b3b56274e272) `d3f2390` | `Config.h` |
| 8/19 | **Leo‑John233** | [测试提交](https://github.com/Dcmdan/OnStep/commit/b441a08c30fd5678f5fd263b83df9d6b413009c4) `b441a08` | `OnStep4.24固件-哆啦A梦/Config.h` |
| 8/19 | **Leo‑John233** | [测试提交](https://github.com/Dcmdan/OnStep/commit/0c191e7fa3fee4ae5065f90006d0bdc0cdbf477d) `0c191e7` | `Config.h` |
| 8/19 | **zhoufeng** | [add clang-format](https://github.com/Dcmdan/OnStep/commit/5f41befebef96c0fd0456b9f07fe6cadab0fd707) `5f41bef` | `多个目录` · 211 |
| 8/19 | **zhoufeng** | [add clang-format](https://github.com/Dcmdan/OnStep/commit/6b0845eb2c682c665d792dba33bb36556b6e7df3) `6b0845e` | `多个目录` · 5 |
| 8/19 | **zhoufeng** | [release 0818: 去掉脉冲模式下的轴共享功能](https://github.com/Dcmdan/OnStep/commit/b887495a2ac47e7e7dc8b3852c919715aa15d648) `b887495` | `多个目录` · 8 |
| 8/19 | **zhoufeng** | [release 0811: 修复tmc2209细分问题](https://github.com/Dcmdan/OnStep/commit/12f911ebe97254755fde7ad13de3c712e691cfcc) `12f911e` | `多个目录` · 8 |
| 8/19 | **zhoufeng** | [release 0804: 修复功能解耦导致的bug](https://github.com/Dcmdan/OnStep/commit/3cdbbaa5afb37b20f5539240d61e245c6f42f685) `3cdbbaa` | `多个目录` · 9 |
| 8/19 | **zhoufeng** | [release 0803: 功能解耦中天限位规避](https://github.com/Dcmdan/OnStep/commit/3b9c41c4083ad94d7ed5840936ba3371b4117cf4) `3b9c41c` | `多个目录` · 8 |
| 8/19 | **zhoufeng** | [release 0801: 基于0717修复zwo适配](https://github.com/Dcmdan/OnStep/commit/c6b013849773713054384c9d23b1a48ef067d098) `c6b0138` | `多个目录` · 5 |
| 8/19 | **zhoufeng** | [release 20260729: 基于0717做出功能解耦](https://github.com/Dcmdan/OnStep/commit/647ed1c74573384a60c9d1f8b8e96ad0800b5797) `647ed1c` | `多个目录` · 7 |
| 8/19 | **zhoufeng** | [release 20260717: goto问题修复](https://github.com/Dcmdan/OnStep/commit/b589681db167a49487972aa5b49b1ed289bff3c5) `b589681` | `多个目录` · 7 |
| 8/19 | **zhoufeng** | [release 20260712](https://github.com/Dcmdan/OnStep/commit/cceb9e06043ce7d4bb295e9e8296a7ccd75b35ab) `cceb9e0` | `多个目录` · 12 |
| 8/19 | **zhoufeng** | [all files refresh to LF](https://github.com/Dcmdan/OnStep/commit/402b1da6bf9eed6d983c76e4ed9223e65c2aa3a7) `402b1da` | `多个目录` · 3 |
| 8/19 | **zhoufeng** | [add SmartWebServer](https://github.com/Dcmdan/OnStep/commit/c7b4a89f6637b068f59a1e36cd11614bf913fb3f) `c7b4a89` | `.gitignore + SmartWebServer` · 338 |
| 8/19 | **zhoufeng** | [add librarys](https://github.com/Dcmdan/OnStep/commit/4d9728e9b92a6e0a49fd60237dff196a61c38e86) `4d9728e` | `libraries` · 3804 |
| 8/19 | **zhoufeng** | [release-20260530](https://github.com/Dcmdan/OnStep/commit/8e4a9fa6888c1abdc0d35e895e221adf491634c7) `8e4a9fa` | `多个目录` · 13 |
| 8/19 | **zhoufeng** | [LY 1.3](https://github.com/Dcmdan/OnStep/commit/e83e2d03dc145631f5062cc3b879d702fdaaf2c3) `e83e2d0` | `多个目录` · 12 |
| 8/18 | **Leo‑John233** | [修改代码注释翻译](https://github.com/Dcmdan/OnStep/commit/9e2b3f34c6c8d50d4c581499361100fca9352b4f) `9e2b3f3` | `OnStep4.24固件-哆啦A梦` · 2 |
| 8/18 | **Leo‑John233** | [修改代码注释翻译](https://github.com/Dcmdan/OnStep/commit/ad1bbe9b84f3456a23084dcbe559b57cbd8d9f4e) `ad1bbe9` | `Validate.h + src` · 2 |
| 8/18 | **Leo‑John233** | [Revert "恢复 OnStep 4.24 细分逻辑并关闭 Goto 细分"](https://github.com/Dcmdan/OnStep/commit/b5a516fca210f9f857dc49629270623856597b33) `b5a516f` | `OnStep4.24固件-哆啦A梦` · 3 |
| 8/18 | **Leo‑John233** | [Revert "恢复 OnStep 4.24 细分逻辑并关闭 Goto 细分"](https://github.com/Dcmdan/OnStep/commit/a2b2d442bb79c7d9ca9d4e1fa81b4ce2c2815219) `a2b2d44` | `多个目录` · 3 |
| 8/18 | **Leo‑John233** | [恢复 OnStep 4.24 细分逻辑并关闭 Goto 细分](https://github.com/Dcmdan/OnStep/commit/54292e5997a016bcc1e3acb0f61f03e03c235f52) `54292e5` | `OnStep4.24固件-哆啦A梦` · 3 |
| 8/18 | **Leo‑John233** | [恢复 OnStep 4.24 细分逻辑并关闭 Goto 细分](https://github.com/Dcmdan/OnStep/commit/f4a8d81a3286b2a6930678b35c78c4d76a0d2b8f) `f4a8d81` | `多个目录` · 3 |
| 8/18 | **Leo‑John233** | [修复 MaxESP3 TMC2209 跟踪抖动](https://github.com/Dcmdan/OnStep/commit/052ab28f8307f17e2a8a9a92095ee460cecf82af) `052ab28` | `OnStep4.24固件-哆啦A梦` · 4 |
| 8/18 | **Leo‑John233** | [修复 MaxESP3 TMC2209 跟踪抖动](https://github.com/Dcmdan/OnStep/commit/82aaeb9d2136417827e8138a3bc1787b89e7010e) `82aaeb9` | `多个目录` · 4 |
| 8/17 | **Leo‑John233** | [修改readme.md](https://github.com/Dcmdan/OnStep/commit/d8d21c5bc91ebf47a62af0226a2a88a8dc84f320) `d8d21c5` | `OnStep4.24固件-哆啦A梦` · 2 |
| 8/17 | **Leo‑John233** | [修改readme.md](https://github.com/Dcmdan/OnStep/commit/1cb705514a17d935de9d42ac6aec1241283c15b7) `1cb7055` | `example.md` |
| 8/17 | **Leo‑John233** | [修改readme文件，添加了一个新的示例文件example.md](https://github.com/Dcmdan/OnStep/commit/24338faa5ba036bf106cf61148eb608e5843133d) `24338fa` | `OnStep4.24固件-哆啦A梦` · 2 |
| 8/17 | **Leo‑John233** | [修改readme文件，添加了一个新的示例文件example.md](https://github.com/Dcmdan/OnStep/commit/db46a7778e6f459984e3c9ba7d2b2aed9b669ee5) `db46a77` | `example.md` |
| 8/16 | **Leo‑John233** | [修改注释](https://github.com/Dcmdan/OnStep/commit/d987f8be50f8e918083c58272c0bad6ccc2ae093) `d987f8b` | `OnStep4.24固件-哆啦A梦` · 4 |
| 8/16 | **Leo‑John233** | [修改注释](https://github.com/Dcmdan/OnStep/commit/1049e170b126f82ac85f567ad918fa05d6b10c43) `1049e17` | `多个目录` · 4 |
<!-- RECENT_CHANGES:END -->

## 🟩 Repository Activity

![Repository Activity](./assets/repository-activity.svg)
