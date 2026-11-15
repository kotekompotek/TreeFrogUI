# Перенос TreeFrogUI и периферии на Linux 7

## Актуальное продолжение 2026-11-15 (приоритет над историей ниже)

- **Камеры запрещены пользователем.** Не открывать и не заявлять visual UI PASS.
- Git верхнего уровня уже инициализирован; держать sources/plans/acceptance summaries
  актуальными по AGENTS.md. Payload, binary/runtime, raw captures и секреты local-only.
- Hardware accepted slices: DRM scanout (KMS v5 IRQ-fix), silent ALSA DMA v3,
  двусторонний USB CDC v4, headless Gambatte/FCEUmm, glibc video backend v3.
  Это отдельные срезы, НЕ совместная приёмка UI/game/audio/input/MTP.
- UI v7: core loaded, backend frames=1; missing legacy framebuffer errors.
  Причинность не доказана. V6 измерил main nanosleep ~14.5ms: не long-timer stall.
- Существующие ui_core_trace_test_v1/harness, synthetic core и trace-v1 повторно
  исполнены БЕЗ rebuild через actual saved console glibc в QEMU-user. Контроль
  без preload и наблюдение с preload PASS; все runtime/artifact hashes совпали.
  UI_CORE_TRACE_FORWARDING_VERIFIED.json; raw ui_core_trace_verify_v2/result.json.
  Это synthetic forwarding, НЕ выполнение настоящего FrogUI/железная приёмка.
- Новое: opt-in R36_UI_CORE_TRACE, только дочерний LD_PRELOAD, несовместим с
  R36_UI_TIME_TRACE. Нейтральный SysV input, SD RO, settings-copy в RAM, 16s window.
- Новый payload/kernel_ui_core_trace_v8: только PID1 rebuild; initramfs34348B
  в исходном40023B slot kernel_display_kms_vm_v6_irqfix. Патч от v7 отказал
  (34348>34325) без output; использован original verified source, код ядра неизменен.
  DRM backend и trace library переиспользованы. Cold wrapper kernel_cold_ui_core_trace_v8,
  bootm/gzip, cold emulation/native fallback, ELF/flat/hash reversal PASS.
- Офлайн pytest:219 passed,9 skipped (Windows отсутствует native Linux C runtime);
  первый прогон218 passed/1 failed/9 skipped: устаревшая проверка #ifdef заменена
  на equivalent exclusive #elif opt-in, production safety не ослаблена.
- **Hardware trace v8 завершён:** UI_CORE_TRACE_v8_RESULT.json. На реальной
  Linux7 retro_run entry/return до12420, videos=1. Первый callback640x480/RGB565
  непустой:585299bytes, FNV1a0f4e3334; DRM submitted1. В этом instrumented trial
  frontend loop продолжает работать, core не выдаёт следующие callbacks.
  Не считать run count benchmark: preload может влиять на тайминги.
- Watchdog/native restore/stock MTP/6boot hashes PASS, host boot cleanup writes=false;
  picoarch/core/settings hashes до/после совпали. RSS8656kB/swap0, child exit0.
  Камера не использовалась, visual/navigation/audio не приняты.
- **Следующий шаг:** actual FrogUI retro_run draw conditions, initialization/worker
  state и legacy framebuffer path. Missing-fb errors остаются, sole cause не доказана.
  Не повторять unchanged trial, не подменять fb ioctl/dummy success и не clamp timers.

Актуальная единая очередь: REMAINING_AND_TESTS.ru.md — интерфейс, кнопки,
звук, эмуляторы, **USB**, ФС и питание. USB CDC Linux7 принят отдельно;
MTP при возврате в stock не является подтверждением MTP Linux7.

Ниже сохранена история; старые запреты/разрешения доступа и pending-статусы
не перекрывают этот раздел и более поздние измеренные отчёты.

## Offline USB и emulator-backend 2026-11-14

- USB private glue patch: удалены Linux IRQ-depth platform callbacks и trailing
  disable_irq. Core owns request_irq/controller masks; stop calls disable under
  musb->lock, синхронный disable_irq мог ждать ISR на том же lock. Контракт
  optional callbacks и source anchor/idempotence/failure checks проверены.
  Это статический дефект, не подтверждённая причина старого enumeration failure.
- --usb-probe isolated kernel build в owned VM: USB0 peripheral/PIO/PHY/CDC ACM,
  USB1 disabled, нет UART/input/audio/display takeover/host/MTP/mass-storage.
  usb_cdc_init.c ждёт UDC bounded, отказывается выбирать среди нескольких,
  отвечает PING/PONG32hex, через12с unbind и пишет fresh SD report, watchdog не трогает.
- usb_cdc_host.py открывает только explicit COM с exact VID/PID/serial и требует
 3 random challenge replies. Configfs bind/device ping count НЕ заменяют host proof.
  Сам tool офлайн не запускался, устройства/микрофон/камера не открывались.
- fetch_usb_build.py strict allowlist/config/ELF/initramfs/provenance checks ready;
  аппаратная enumeration и двусторонняя передача ещё НЕ приняты.
- emulator_backend_smoke_v1/suite.json PASS:4 real unchanged MIPS cores x2 modes,
 120 frames через libretro1555/8888/565 conversion + real new video backend/scaler.
  Только DRM ioctls/device mocked, production driver library не подменяется.
-186 full pytest PASS на момент первого полного прогона, затем добавлены configfs
  syscall-model setup test и USB result tests; общий прогон повторить.

## Offline input/emulator acceptance 2026-11-14

Пользователь временно не может подключить консоль: звук отложен в
AUDIO_TEST_TODO.ru.md, не опрашивать MTP/не записывать микрофон.

- keys_evdev_sysv_integration_v3.json:8 настоящих Linux uinput/evdev/SysV случаев
  PASS, включая initial held state/2sources/alias/release/disconnect cleanup.
- keys_core_integration_v1.json: native Linux publisher -> actual SysV word ->
  real MIPS Gambatte -> synthetic Game Boy CPU program, press/release PASS.
  MIPS publisher through QEMU-user EVIOCGID returns ENOTTY: do NOT claim end-to-end
  native MIPS input or physical serializer acceptance from the host test.
- emulator_smoke_v3/suite.json:4 unchanged cores (Gambatte/Gearboy/FCEUmm/QuickNES),
 120 frames x2 modes (A press-release/neutral), real video/nonzero PCM/input callbacks,
  ROM RAM flags, save-state/mutate/restore PASS.8 execution cases, not just dlopen.
- Original synthetic GB/NES ROM sources make_synthetic_roms.py; no commercial
  ROM/BIOS copied. Runtime MIPS Debian libraries from existing local sysroot/btbundle,
  not actual console userspace. No speed/real games/hardware claim.
- calibrate_legacy_keys.py requires fresh complete capture and human labels of
  press event ordinals with subsequent release. Never guesses serial bit order.
-173 pytest PASS. Full UI/picoarch launch/new-kernel GPIO still pending device access.

## Frontend/input/audio continuation 2026-11-14

Состояние: FRONTEND_PORT_STATUS.json. Не путать готовые compatibility components
с запуском полного интерфейса.

- Новый video_drm_backend.c собран glibc/MIPS hard-float в
  analysis/driver_port/driver_r36_drm_video_v2.so. Обязательные3 video exports
  подтверждены статическим caller ABI; optional g_render/GE/sound отсутствуют.
  Это реальный DRM submit и RGB565 scaler, не dummy-success. Actual-source mocked
  DRM test и MIPS glibc dlopen/error-path PASS. Hardware library submit/UI НЕ tested.
- legacy_keys.c — новый evdev->SysV4B publisher, явная calibrated mapping,
  exclusive segment и release-on-fault. Конфликты между источниками/alias keys,
  repeat и bounds проверены host C tests. Реальный serial order неизвестен.
- Отдельный r36-display-input.dts исключает power/LCD/amp/audio pins и USB.
  Raw serial positions BTN_TRIGGER_HAPPY1..12, directGPIO2/7/11. Input-probe kernel
  собран и cold rollback проверен. Hardware попытка остановилась на missing MTP
  ДО upload и изменения boot-файлов; ничего не запускалось.
- Native ALSA source staged audio_driver_source_v1: actual PCM/IRQ/DMA logic,
  syscore speaker policy удалена, gain0/mute, explicit allow_takeover и DT disabled.
  GPIO19/15 и единоличное владение AVP audio требуют отдельной проверки.
  VM compilation started with --audio-source; completion receipt required.
- Новые flags --input-probe/--audio-source по умолчанию off. Verified display
  candidate/frozen bundle/companion UI sources не менялись.144 pytest PASS,
  ещё новый audio archive opt-in test добавлен после этого прогона.

Следующие реальные шаги: восстановить MTP, принять input inventory/physical serial
mapping; независимо проверить backend harness на DRM, потом прежний picoarch с
PICOARCH_DRIVER. Audio loader picoarch отдельный: video override не заменяет звук.
Нельзя экспортировать заглушки sound_driver_* ради фиктивного запуска UI.

## Цель и текущая граница

Сохраняется существующий TreeFrogUI: picoarch + frogui_libretro.so, настройки,
шрифты и изображения. Реальный интерфейс под Linux7 пока не запущен. Успех
минимального NOR-старта/PID1/SD не означает готовность экрана, аудио или кнопок.

Пользователь отложил доступ к консоли («Пока без консоли»). После этого новые
образы на устройство не устанавливались; выполняются локальные сборки и проверки.

## Подтверждённый stock ABI

Источник: native read-only probe на stock4.4 #23:
`runtime_20261113T041911Z/inventory.txt`. Программа успешно выполнена на консоли,
все GET-ioctl framebuffer вернули0. Это измерение stock, не драйверный PASS Linux7.

| Объект | Измерение |
|---|---|
| UI | /cubegm/picoarch + /cubegm/cores/frogui_libretro.so |
| Backend | driver_gb350.so; активен также tfshim_gb350.so |
| fb0 |640x480, RGB565, pitch1280, phys0x02f92000,14749264B |
| fb1 |640x480, ARGB8888, pitch2560, phys0x01a00000,1228800B |
| GE | /dev/ge, MMIO18806000; в maps также offset01980000/length3c000 |
| Кнопки | /proc/bus/input/devices пуст; cubevol читает GPIO и публикует SysV shm |
| Звук | штатные /dev/sndC0i2so и /dev/auddec, не ALSA /proc/asound |

FB1 находится внутри обычного Linux RAM-диапазона. В новых диагностических DTB
зарезервированы0x01a00000/0x12c000 и консервативно наблюдавшийся GE mmap-диапазон
0x01980000/0x3c000. Последний ещё требует подтверждения device mmap semantics;
это исключение из allocator, а не запись в неподтверждённые регистры GE.

В минимальном frozen kernel `CONFIG_SYSVIPC` выключен. Для совместимого UI нужны
SysV shm/messages/semaphores; в новом source-build profile этот параметр включён.
В frozen kernel уже включён MIPS_FP_SUPPORT; запуск существующего hard-float UI
всё равно требует собственной аппаратной проверки.

Статический ELF inventory: `UI_ABI.json`. Поиск DWARF-прототипов высокоуровневых
экспортов не дал их типов: `DRIVER_UI_SIGNATURES.json` явно содержит missing.
Три сигнатуры документированы рабочим tfshim.c: video_driver_disp_frame,
sound_driver_init, sound_driver_playframe. Остальные нельзя заменять догадками.

## Первый реализуемый срез: AVP transport

`scripts/kernel_lab/amprpc_driver/r36_amprpc_poll.c` — настоящий исходник
polling-драйвера с coherent DMA packet и sysfs-диагностикой. Это не generic ioctl
proxy и не готовая реализация всех AVP-устройств.

- Probe только проверяет ресурсы, отображает MMIO, выделяет одну страницу;
  обращение к peer не выполняется автоматически.
- DT compatible r36lab,amprpc-poll; два точных ресурса18800800/100 и18866800/100.
  Node в source-build DTB по умолчанию disabled.
- test_roundtrip принимает только1 и посылает один open заведомо отсутствующего
  имени. Запись GPIO/DSI/audio/persistentmem/standby не производится.
- Неподходящая группа pending, чужой packet pointer, неверные state/opcode,
  timeout дают отказ. Callback function pointers не вызываются.
- Диагностика одноразовая. Опубликованная DMA-страница не перерабатывается после
  timeout/unload: peer ещё может держать её адрес. Она сохраняется до reset.
- sysfs last_result показывает состояние NOT_RUN/результат, а не фиктивный успех.

`scripts/peripheral_lab/avp_probe.c` — независимый userspace bring-up клиент.
В stock разрешён только --inspect. Отправка запроса разрешена только в собственном
Linux7 PID1. Anonymous page pinning, pagemap и cacheflush дают общий physical
packet; обращение идёт через uncached /dev/mem mapping. Результат записывается
на SD; packet остаётся закреплённым до watchdog reset.

Первый cold-пробник работает на уже проверенном kernel code с заменённым только
встроенным initramfs: `kernel_avp_probe_profile_v3`, wrapper `kernel_cold_avp_probe_v3`.
Kernel ELF и flat image патчатся согласованно, меняются только gzip blob и его
length word; старые RAM-handoff .ko/ctl и stale compressed kernel не копируются.
Это не полный rebuild kernel и не UI-совместимый kernel: SYSVIPC в нём остаётся
как в frozen baseline. Он нужен для изоляции проверки AVP.

Cold wrapper сохраняет раннее восстановление stock-файла и native backup bootm
при отказе. Все новые кандидаты имеют hardware_verified=false/deployed=false.

## Готовые offline artifacts

| Каталог в payload | Назначение |
|---|---|
| kernel_cold_avp_probe_v3 | Изоляция userspace RPC на прежнем проверенном kernel code; новый init и display reservations |
| kernel_port_avp_vm_v1 | Полный source build7.2.0-rc5-r36port, SYSVIPC=y, userspace test, kernel RPC node disabled |
| kernel_port_avp_module_vm_v1 | Тот же kernel/module ABI; RPC node okay, init argument --kernel-probe, extra SD file r36_amprpc_poll.ko |
| kernel_cold_port_avp_vm_v1 | Зашифрованный NOR wrapper source-build userspace профиля |
| kernel_cold_port_avp_module_vm_v1 | Зашифрованный NOR wrapper kernel-module профиля |

Source-build kernel SHA256990e005eb3035748e6440849ca2dbe178f2c40358da6538017f6cd5ed0f51c2d.
Module SHA256b28ee39a05f9f9a8852227973d605332963c85300045df2787c7bbc2dbcfeeda,
vermagic `7.2.0-rc5-r36port mod_unload MIPS32_R2 32BIT`.
Build receipt: payload/kernel_port_avp_vm_v1/build_receipt.json.

В module-mode PID1 не отображает mailbox MMIO сам: он загружает соответствующий
модуль и работает только через sysfs. Таким образом, userspace и kernel client
не управляют одним mailbox одновременно. После записи log закрываются оба SD
stdout/stderr descriptor, затем SD синхронизируется и размонтируется/переводитсяRO.
PASS userspace/kernel разбираются раздельно по полным строкам, fresh run_id и footer;
старая, обрезанная или смешанная запись не даёт аппаратного PASS.

## Проверки первого среза

- Packet builder `amprpc-open-wire.h` побайтно совпал с исполнением оригинального
  avp_open0x802bad04 в7 сценариях, включая границу4096B и отказ oversized path.
  `amprpc_open_wire_verified.json`. Это wire-construction oracle, не ответ AVP.
- Существующий mailbox planner сверяется с оригинальным ISR, включая wrong-group
  pending. Crypto + planner:48 pytest PASS с отдельным basetemp в analysis.
- Для `kernel_cold_avp_probe_v3` и обоих source-build cold wrappers прошли original bootm/header/CRC/gzip,
  pre-kernel restore + real kernel head до start_kernel и native-decrypt fallback.
- profile_validation.json подтверждает init в newc archive, patch bounds,
  совпадение ELF/flat, framebuffer reservations и неизменность всех frozen hashes.
-4 ELF normalization regression tests и4 acceptance parser tests прошли;
  вместе с crypto/planner это56 pytest checks, плюс7 native open-wire cases.
- Userspace RPC, kernel RPC module и фактический AVP response под Linux7 пока
  не проверены на устройстве.

## Порядок дальнейшего переноса

1. Read-only snapshot mailbox на stock, затем один isolated Linux7 open-negative
   roundtrip, проверка state/ack/coherency и автоматического возврата. После этого
   sysfs-тест kernel module на точно соответствующем kernel build.
2. Экран: наследовать panel/MIPI timings от загрузчика; сверить layer descriptors,
   владение fb0/fb1/GE и read-only framebuffer info. Первый вывод — тестовая
   RGB565-картинка с read-back; затем framebuffer/DRM backend для прежнего UI.
3. Звук: восстановить typed ioctl/kshm/mmz либо адаптировать native I2S/ALSA.
   CS4344/left-justified и GPIO3/4/5 подтверждены нашим DTB. Native reference
   зависит от другого syscore firmware для amplifier: его нельзя подключать
   без адаптации. Speaker GPIO19/headphone15 и mute проверяются отдельно.
4. Кнопки: GPIO data9/clock8, плечевые11/7, volume12/13, FN2, power14. Нужна
   проверка каждого serialized bit и timing на нашей плате. Для прежнего picoarch
   потребуется совместимый publisher ftok(/tmp/joy_key,'a')/4B; B=0x4000 из tfkey.c.
   Evdev сам по себе не заменяет этот consumer ABI.
5. USB: сначала CDC/командный диагностический канал, затем FunctionFS/MTP;
   старые kernel4.4 gadget modules в Linux7 не переносятся бинарно. Host/OTG —
   отдельная реализация, upstream glue поддерживает только peripheral/PIO.
6. Backlight, ADC/battery, headphone/amp, корректные shutdown/sleep и чистая FAT
   handover. Power latchGPIO1 и LCD resetGPIO6 не трогать как часть кнопочного теста.
7. Финальная совместная приёмка прежнего UI, навигации, звука, игр, saves, USB,
   idle/sleep/restart, длительного SD/DMA/IRQ прогона и полного power-off/on.

Нельзя blindly forward ioctl по _IOC_SIZE: вложенные pointers и bare legacy
команды требуют известной схемы. Нельзя возвращать0 из неработающих методов,
чтобы объявить UI портированным.

## Исходники и сборка

Найдена публичная native реализация DRM/GE/I2S/input:
https://github.com/csnewman/gb350-linux, pinned bff93e84fe79c9e67bde284dfe4d58054b62282b.
Reference checkout: analysis/gb350-linux-reference, без правок. BoardGB350 v1.22
имеет256MiB; наша плата128MiB и другие boot aliases. Релиз/DTB/AVP firmware оттуда
на нашу карту не устанавливались. Наличие исходника — не hardware PASS нашей платы.

Сборка userspace доступна напрямую на Windows через Zig0.17, target
mipsel-linux.4.4-musleabi/-march=mips32r2/-msoft-float. Статический inventory
прошёл на настоящем stock. Shared backend для старого glibc UI требует отдельного
согласованного ABI; статические musl tools не являются LD_PRELOAD библиотеками.

WSL ubmips по-прежнему StopPending, её процессы не перезапускались. Отдельная
workspace-owned Alpine/QEMU/WHPX build VM имеет native clang20 и GNU MIPS as2.44.
GNU assembler нужен из-за unsupported forward-immediate expressions genex.S в
LLVM integrated assembler. Изменение kernel exception code для обхода не делалось.
modules_prepare генерирует module.lds перед external module final link.
LLD оставлял PT_LOAD file span поверх trailing NOBITS. Packager проверяет точное
совпадение initialized prefix, отсутствие initialized sections в отбрасываемом
хвосте и корректирует толькоp_filesz; p_memsz/код сохраняются. Четыре regression
tests проверяют этот случай, GNU layout и отказ при несовпадающих/initialized данных.
VM descriptors/ключи/PID: analysis/kernel_build_vm_v1/state.json; SSH только
127.0.0.1:22222. HTTP отдаёт только allowlisted boot resources, не каталог с ключом.

Перенос UI source не выполнялся в пустом detached frogui submodule. Сначала
сохраняется existing binary/asset ABI через новый backend/совместимые сервисы;
изменения самих companion source trees требуют их canonical checkout по AGENTS.md.

## Hardware continuation 2026-11-14

Пользователь разрешил watchdog-опыты и приватную локальную камеру.
Пассивный snapshot аппаратно PASS; cold trials KMS v1/v2/v3/v4 всегда вернули
штатное ядро и MTP,6 boot hashes исходные без host cleanup writes.

- v1: DRM probe отказал на panel-timing. Исправлено DT width-mm/height-mm=0
  (размеры неизвестны, значения не выдумываются) в display_driver_source_v4.
- v2: card0 зарегистрирована, EFAULT userspace. Исправлены props/value arrays
  второго GETCONNECTOR и включён64-bit off_t; added checked_ioctl stage reports.
- v3/v4: SETCRTC и WAIT_VBLANK rc0, active descriptor02f90400, pixels01500000,
  RGB565/640x480/pitch1280, timing stable, flip_timeouts0. V4 камера с exposure-6
  показала цветные полосы и последующий возврат штатного меню. Private evidence:
  display_visual_kms_v4.json. Полный scanout PASS false: IRQ counters0, до hash
  не дошли. Не выдавать изображение за полную UI/DRM приёмку.
- Root cause IRQ accounting статически подтверждён: irq-hc16xx-intc.c использует
  handle_percpu_irq для device lines, tot_count остаётся0; proc.c подавляет counts.
  Overlay изменяет mapping на handle_simple_irq без MMIO/ack изменений.
- Новый отдельный кандидат kernel_display_vm_v6_irqfix / KMS variant и cold
  kernel_cold_display_kms_v5_irqfix **аппаратно PASS**: display IRQ2->18/MMC213/ERR0,
  CPU/DMA pixel hashes8d21d5c5, scanout PASS. Камера подтвердила полосы и возврат
  штатного меню. DISPLAY_HARDWARE_VERIFIED.json; watchdog30с вернул stock/MTP,
 6 boot hashes исходные, host_cleanup_wrote_boot_file=false. Не full UI acceptance.
 137 pytest PASS; actual built irq source SHA256
  356a97acc25f3691b1554a06ec414206dc3e6b8d50ef25932529572863acc16d.

Авто-fsck: новые исходники/статический CP437 fsck, regular-image tests и staged
RAM PID1 готовы частично. Production writer disabled, в kernel не встроено:
analysis/driver_port/fat_boot_guard_STATUS.json. Пользователю не обещать уже
установленное самовосстановление. Watchdog check-only сохраняется, writer нельзя
прерывать таймером; предварительная аппаратная приёмка обязательна.

## Продолжение после последней OpenCode-сессии, 2026-11-13

Сессия OpenCode проверена read-only в локальной opencode.db; последняя работа —
`display_driver_source_v3` и `display_probe.c`. Продолжение довело незавершённые
сборочные проверки до сохранённых результатов, без доступа к консоли:

- Возобновлена существующая QEMU VM, ext4 диск подключён без форматирования.
  WSL теперь отвечает, но сборка использует прежний clang20/GNU as в VM.
- MIPS pattern selftest реально выполнен `qemu-mipsel -cpu 74Kf`: PASS/exit0.
  `analysis/driver_port/display_qemu_selftest_20261113.json`. Это НЕ эмуляция DE/DSI.
- После остановки VM обнаружены zero-length archive/exit/object files. Первое
  пересобранное ядро с пустым DRM .o было отклонено по отсутствию .r36abi.
  `payload/kernel_display_vm_v1/VALIDATION_FAILED.json`: **не использовать**.
- `vm_build_kernel.sh` теперь чистит внешние modules, проверяет gzip и выполняет
  sync до объявления завершения. Чистая повторная сборка exit0.
- `payload/kernel_display_vm_v2/build_receipt.json`: Linux7.2.0-rc5-r36disp #7,
  kernel SHA256b694948abe6fdb75c55507d9358b5dd417dadad97b38d8d944e5b4ac4178d20a,
  DRM module963e2b4c38d4b273a6fa184f680729bd4c82a384eca24d916de7e004131627a8.
 110 module imports найдены в kernel exports, MIPS probe/module ioctl ABI совпали,
  embedded initramfs/ELF/flat/source hashes/DT проверены.
- `kernel_display_vm_v2` пассивный: display/RPC disabled. Отдельный
  `kernel_display_kms_vm_v2`: explicit --display-kms-probe, display okay,
  RPC disabled, extra device file r36_hc16xx_drm.ko. KMS hardware не запускался.
- Новый fetcher `scripts/peripheral_lab/fetch_display_build.py` проверяет архив
  allowlist, hashes, provenance, exports, ioctl ABI и профиль.102 pytest PASS для
  kernel_lab+peripheral_lab с реальными artifacts; отдельно14 crypto tests PASS.
- `payload/kernel_cold_display_passive_v1`: bootm/header/gzip PASS;8 cold
  success/fault scenarios и native-decrypt fallback PASS. Реальный kernel head
  достигает start_kernel в Unicorn; file APIs заменены stubs.
- Все62 frozen bundle artifact hashes неизменны. Ничего не установлено на консоль.

Следующий аппаратный шаг: согласовать доступ к устройству, сначала пассивный
snapshot display в stock/собственном ядре, затем отдельно KMS.
В run_restored_cold_trial.py добавлены очистка stale display report и сбор
r36-display-probe.txt; peripheral_result.display_result проверяет fresh run_id,
полный footer/probe_rc, release, отдельный passive/KMS режим, load/modeset,
совпадение DMA/CPU hash, рост IRQ и raster_progress. Старые/обрезанные/смешанные
результаты отвергаются. Физическое изображение всегда NOT_TESTED без отдельной
визуальной приёмки. Последний общий прогон kernel/peripheral/crypto:130 PASS.
Сам cold boot proof ещё не означает display PASS. Визуальное подтверждение панели
и прежний UI не заменяются совпадением DMA/CPU pixel hash.
