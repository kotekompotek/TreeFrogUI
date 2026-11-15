# Передача работы: собственный Linux для HC16E310 / SF3000-клона

## Повтор v11 по явному запросу пользователя

- Пользователь отходил во время первого опыта и попросил «Еще раз сделай».
  Разрешён один unchanged repeat для собственного наблюдения экрана, без камеры.
- Проверены hashes исходного cold image и всех source-profile artifacts, оба
  existing cold/fallback reports PASS. Никаких rebuild/нового encrypted image.
- Новый trial folder payload/kernel_cold_ui_live_scanout_v11_repeat1 содержит
  точную копию verified cold candidate v11; session_tag image прежний, run_id
  генерируется свежий. Старый trial/evidence не переписываются.
- **Repeat завершён:** UI_LIVE_SCANOUT_v11_REPEAT1_RESULT.json,
  run_idad2ed2b6d54646b9bb4ed82c8d9bd74e. First+late digital PASS/hash0f4e3334,
  late10040ms/run8460, native restore/watchdog stock MTP/6boot и3UI hashes PASS,
  host_cleanup_wrote_boot_file=false. No rebuild, no camera.
- **UI appearance PASS по прямому наблюдению пользователя:** «интерфейс есть,
  вижу недавнюю игру», затем явно подтвердил «до автоматического перезапуска».
  Это реальный diagnostic Linux7 window, не stock после возврата. Evidence type:
  user eyewitness, не camera/assistant visual inspection и не вывод из hashes.
- Scope только appearance прежнего UI с recent-game content. Navigation/input,
  audio и actual game execution НЕ проверены, power-cycle НЕ accepted.
- **Следующее:** physical input calibration/navigation independent slice;
  затем audio/game integration. Не продолжать black-screen diagnosis как будто
  appearance ещё не доказан. Камеры по-прежнему запрещены.

## Live scanout v11 2026-11-15 (новее v10)

- User «делай, я сам скажу что на экране». Камеры не разрешены/не используются;
  human visual observation pending, не выдумывать и не выводить из цифровых hashes.
- ui_live_checkpoint.h opt-in R36_UI_LIVE_CHECKPOINT: monotonic10s после первого
  callback, poll every60 real retro_run; один synchronous call в уже загруженный
  backend (RTLD_NOLOAD). Нет new thread/signal/input/extra frame/timer modification.
- Backend opt-in r36_scanout_live_checkpoint проверяет submitted_frames1, lock,
  late_live hashes/health/raster. v10 before_cleanup сохранён исторически отдельно.
- v11 source kernel_ui_live_scanout_v11: kernel/DTB/PID1 от v10 без пересборки,
  изменены только backend+observer. Native runtime load/fail-closed/forwarding PASS;
  Linux scheduling mock -Wall/-Wextra/-Werror PASS (one shot,10s,NOLOAD).
- Cold wrapper kernel_cold_ui_live_scanout_v11 bootm/gzip/cold8/native fallback PASS;
  pytest237PASS/10SKIP. No-trace actual backend mock PASS. Host C test first
  failed due cross-libc headers with -I; -idirafter corrected search, no source workaround.
- Перед boot пользователь предупреждён смотреть от первого reboot до stock return,
  кнопки не нажимать. **Один v11 trial завершён:** UI_LIVE_SCANOUT_v11_RESULT.json,
  run_id7582265034904267972c2ceeace26843. First+late_live PASS: elapsed10031ms,
  run8460/frames1, source/mapped/DMA hashes0f4e3334 совпали в обеих точках,
  active/programmed02f90400 unchanged/pixel01500000/timing1/on1/timeouts0/raster1.
  Это две цифровые выборки, не continuous monitoring и не physical panel proof.
- Watchdog/native restore/stock MTP/6boot hashes и3UI hashes PASS, host writes=false.
  User visual observation **PENDING**: спросили, что видно до stock return,
  ответа ещё не было. Не выдумывать и не записывать visual PASS заранее.
- **Следующее:** дождаться user report именно этого trial. Если экран чёрный,
  read-only panel/backlight/layer state investigation; unchanged v11 не повторять.

## Scanout read-back 2026-11-15 (новее state-trace v9)

- User «делай», без камер. Git начат чистым, current branch work/ui-core-trace-v8.
- Новый video_scanout_trace.h, opt-in R36_SCANOUT_TRACE в actual video backend:
  first и before_cleanup hashes callback-source/scaled mapped/uncached DMA;
  health validates active==programmed !=boot, RGB565640x480/pitch/timing/on/timeouts,
  descriptor/pixel RAM bounds; brackets DMA read with health;12x5ms raster samples.
  Только /dev/mem O_RDONLY/PROT_READ, нет added MMIO/state writes. Timing diagnostic.
- Synthetic real C observer WSL PASS -Wall/-Wextra/-Werror: positive/padded pitch,
  corrupted DMA -> mismatch, bad descriptor/missing memory -> fail. Initial mock
  allocation rounding assertion исправлен в test; raw report scanout_mock_v10_result.json.
- Saved console libc MIPS backend load/fail-closed PASS. Old harnessGLIBC2.34 failed;
  новый load-console-v10c связан actual saved libc/libdl; системные libs не менялись.
- payload/kernel_ui_scanout_trace_v10 отличается от v9 ТОЛЬКО backend library.
  Kernel/PID1/DTB/state observer reused. Cold wrapper bootm/gzip/cold8/native fallback PASS.
- Final full pytest235PASS/10SKIP (Linux mock отдельно PASS), focused final10/1skip.
  Windows first run failed sys/mman.h native test; platform guard corrected,
  parser guards не ослаблены. Parser различает first-frame и full two-phase scope.
- **Hardware v10 завершён:** UI_SCANOUT_TRACE_v10_RESULT.json,
  run_id30a437e152884944aa24796101185915. Source callback/backend input/mapped/DMA
  hashes0f4e3334 совпали; nonzero585299. Active=programmed02f90400 !=boot02f92a80,
  pixel01500000/RGB565640x480/pitch1280/on1/timing1/flip_timeouts0/raster progress1.
  **first_frame_verified=true, digital_chain_verified=false**: before_cleanup
  checkpoint в collected log отсутствует. Нельзя выдавать первый вывод за
  end-of-window persistence. Child exit0, RSS8592kB/swap0.
- Native restore/watchdog stock MTP/6boot hashes и3protected UI hashes PASS,
  host_cleanup_wrote_boot_file=false. Камер не было, physical visual НЕ tested.
- **Следующий distinct шаг:** явный bounded late checkpoint пока child alive
  (не cleanup-dependent logging), затем read-only panel/backlight/layer state.
  Не повторять unchanged v10 и не делать вывод о видимости панели по hashes.

## Продолжение state-trace 2026-11-15 (самый новый этап)

- Git baseline f059b5b, ветка work/ui-core-trace-v8. Камеры по-прежнему запрещены.
- Полный FrogUI source локально отсутствует (empty submodule); companion canonical
  paths не менять. REA MIPS provider на Windows unavailable, target закрыт;
  статический анализ сделан существующими pyelftools/Capstone.
- Фактический ELF core MD5 совпал с console403944038926bf102ac498a7376fdafd.
  Static: retro_run имеет idle redraw-elision по unchanged signature/animation/
  toast/transition с usleep1000 и ранним возвратом без video callback.
  Поэтому один callback на neutral input сам по себе НЕ доказывает core failure.
  Адреса/дизассемблированный output только local, не коммитить.
- Новый prepare_ui_state_profile.py: локальный generated profile12 symbol fields,
  bounds/type checks, full-file FNV64/length + code samples. У actual ELF нет GNU
  build ID; fingerprint не cryptographic authentication. Generated headers local-only.
- ui_state_trace.h: O_RDONLY/proc/self/mem + pread, samples before/after real run,
  no writes/input/timer overrides; reject mismatched binary before reading states.
- UI_STATE_TRACE_OFFLINE_VERIFIED.json: synthetic counter0->1->2/flag0->1 PASS,
  callbacks unchanged, wrong actual profile on synthetic core rejected/forwarding PASS.
  Initial verify_v1 FAIL (empty fields bug); fix+verify_v2 PASS, raw retained.
- New payload/kernel_ui_state_trace_v9: ядро/DTB/PID1/DRM backend byte-identical v8,
  только observer changed to state-trace-v3. Cold wrapper v9 bootm/gzip/cold8/
  native fallback PASS. Hardware один trial завершён (см. ниже).
- Final pytest225PASS/9SKIP; focused6PASS; C -Wall/-Wextra syntax PASS.
- **UI_STATE_TRACE_v9_RESULT.json**: run_id66eb7d9d6666488cb5971bf99714d4cf,
  cold/native restore/watchdog stock return/6boot hashes PASS, host writes=false.
  Protected picoarch/core/settings MD5 после совпали. Камер не было.
  Profile bound,44samples: first1->0, last_sig2760972902 stable,
  idle_ticks0->1 then6->7/14->15, transition3/carousel13/animation1,
  toast/screenshot/USB/migration0. retro_run returns до12240, videos1/backend1.
- **Вывод уточнён:** нейтральное меню после первого кадра реально использует idle
  redraw-elision. Отсутствие следующих callbacks НЕ доказательство core failure.
  Причина исторического чёрного экрана остаётся неизвестной; worker role неизвестна.
- **Следующее:** read-back первого кадра в mapped DRM buffer и active scanout
  descriptor/DMA, без камеры/изменения input. Visual acceptance NOT_TESTED.
  Не форсировать redraw, не менять flags ради PASS, не fake fb/audio exports.

## Актуальное продолжение 2026-11-15: Git и core trace (приоритет над историей)

- Пользователь: продолжать от ui_core_trace_test_v1, не пересобирать без нужды;
  **камеры не использовать**. Это перекрывает исторические разрешения ниже.
- Верхний уровень Git инициализирован, initial index существовал без HEAD.
  AGENTS.md уже содержит Keep Git Current. Baseline включает только относящиеся
  к проекту sources/docs/selected summaries. Не добавлять payload/runtime/keys,
  dumps/кадры/third-party; dashboard и generated *.mod.c исключены, local сохранены.
- Готовые harness/synthetic core/r36-ui-core-trace-v1.so переиспользованы.
  verify_ui_core_trace.py: local/VM SHA256 всех7 artifacts/runtime совпали;
  контроль без preload и trace preload на actual console glibc/QEMU PASS.
  UI_CORE_TRACE_FORWARDING_VERIFIED.json, raw ui_core_trace_verify_v2/result.json.
  Это synthetic observer forwarding; provenance rebuild и настоящий FrogUI здесь
  НЕ verified. Не выдавать его за аппаратный результат UI.
- ui_console_init.c: новый child-only R36_UI_CORE_TRACE, исключён одновременный
  time trace; SD RO/RAM settings/neutral SysV/16s bound прежние.
- Собран только новый PID1 r36-ui-core-init-v8. Патч от v7 отказал без output
  (34348>34325B); новый kernel_ui_core_trace_v8 сделан от исходного verified DRM
  kernel_display_kms_vm_v6_irqfix (34348<=40023B). Reversal/ELF/flat/DT/hash PASS;
  код ядра и source не менялись. DRM backend и trace library прежние.
- Cold wrapper kernel_cold_ui_core_trace_v8: bootm/gzip, cold8 scenarios/native
  fallback PASS. Software не означает аппаратную приёмку.
- Pytest219 PASS/9 SKIP; до исправления test #ifdef syntax был218/1fail/9skip.
  Final baseline:158 Python AST parse PASS; JSON проверяются при staging.
  Frozen manifest20 hash entries также PASS; full frozen62 здесь не пересчитывался.
- **Один hardware v8 завершён:** UI_CORE_TRACE_v8_RESULT.json, trial
  kernel_cold_ui_core_trace_v8_trial.json/run_id b634c1bd2e7144619d33235c8139fe5d.
  Real Linux7/PID1: retro_run entry/return до12420, videos=1. Первый callback
  640x480/RGB565/pitch1280 nonzero585299/hash0f4e3334, DRM submitted1.
  В этом instrumented trial frontend loop не блокирован; core не выдаёт
  следующие callbacks. Run count не benchmark, observer может менять тайминги.
- Watchdog/native restore/MTP/6boot hashes PASS, host_cleanup_wrote_boot_file=false.
  Stock4.4.186 #23 подтверждён после; picoarch/core/settings MD5 до/после совпали:
  e154f7afade3f340263d7e0f89373c15 /403944038926bf102ac498a7376fdafd /
  80b1652856ad284baaa3f7000a24db7c. RSS8656kB/swap0/child exit0. Камеры не открывались,
  visual/navigation/audio не приняты. Power-cycle не проверен.
- **Следующее:** исследовать actual FrogUI retro_run draw conditions, initialization/
  worker state и legacy framebuffer dependency. Missing-fb errors не доказывают
  sole cause. Не повторять unchanged trial и не включать fake fb/audio exports.
  Сначала сохранить завершённый проверенный unit в Git, затем новый distinct experiment.


> **Следующий unchanged UI appearance опыт (2026-11-15):** по запросу «делай»
> подготовлен ui_console_init.c и driver_r36_drm_ui_v1.so с frame counters.
> Source kernel_ui_appearance_v1 от verified DRM code (init-only reversible patch),
> cold kernel_cold_ui_appearance_v1 software/fallback9 scenarios PASS.
> **v1 hardware FAIL UI:** kernel/PID1/picoarch/DRM/SDL/SysV started, но FrogUI
> dlopen cannot map zero-fill pages; kernel __vm_enough_memory rejects78970880B.
> Actual ELF RW segment memsz79002780/filesz28768 (~79MB sparse BSS), stock UI
> RSS6136kB/VmSize150360kB со swap131068kB. Camera не показала UI в новом ядре.
> Watchdog вернул stock/MTP/native restore, settings/picoarch/core MD5 unchanged.
> UI_APPEARANCE_v1_RESULT.json. **v2 hardware completed:** RAM overcommit1,
> RLIMIT_AS192MiB/no SD swap позволили dlopen/load/content FrogUI и первый
> submitted frame640x480. RSS8712kB/VmSize108204kB. UI alive8с, graceful exit0,
> но камера НЕ показала меню (темно во время нового ядра). Только partial evidence,
> UI_APPEARANCE_v2_RESULT.json, НЕ appearance/fullUI PASS. Watchdog/native restore,
> MTP/settings/picoarch/core hashes unchanged. **v3 hardware completed:**16с окно,
> at4/8/12с main/input threads sys_nanosleep_time32, worker futex; RSS8712kB
> stable, frames1, menu не виден. UI_APPEARANCE_v3_RESULT.json. Watchdog/native
> restore PASS. Не повторять такой же опыт без новых evidence.
> **v4 time diagnostic ready:** ui_time_trace.c transparently forwards actual
> clock_gettime/gettimeofday/nanosleep/usleep,160 records max, no clamping/fake time.
> MIPS test с EXACT saved console runtime PASS (time_t4/timespec8). Extra
> r36-ui-time-trace.so via child-only LD_PRELOAD, read-only same SD policy.
> v4 hardware completed,watchdog/native restore/stock return PASS. Clock mono
> around2.29s, input usleep8000 works;global160-record trace exhausted by input
> before main problematic sleep,frames1. Source trace now per-thread budget12,
> long sleeps always logged with tid. MIPS forwarding test exact runtime PASS.
> v5 hardware finished:core loaded/frames1, no long sleep through intercepted
> nanosleep/usleep. Clock1 around2.55с after first frame. Watchdog/native stock
> restore PASS. Причина паузы НЕ доказана. Не clamp timers на основании гипотезы.
> **v6 syscall diagnostic prepared:** no preload, /proc/task/syscall + read-only
> /proc/child/mem to decode exact MIPS4166 time32 nanosleep request.16с window,
> SDRO, RAM settings/overcommit as before. v6 initially exceeded init slot,
> sscanf diagnostic replaced with strtol/strtoul (smaller binary), slot now34298
> <=40023;reversible patch + cold/fallback PASS. **v6 hardware finished:** main
> nanosleep request sec0/nsec14509000 (~14.5мс), input8мс,worker futex; НЕ long
> timer stall. Watchdog/native restore PASS. Frames1 still,UI unverified.
> **v7 direct-exec hardware completed:** original PT_INTERP/proc-self-exe/cwd,
> bin/sbin/etc aliases;core loaded/frames1,still no UI menu on camera. Log now
> exposes FrogUI errors opening fd_fb/fb_framebuffer/framebuffer device. Нельзя
> считать их доказанной единственной причиной, но это конкретный missing ABI.
> Watchdog/native stock restore PASS;no host boot cleanup writes. БОЛЬШЕ не
> повторять black-screen cycles без точного нового evidence/изменения.
> Следующее: выяснить обход libretro через legacy fb layer и минимальный реальный
> fb compatibility/native UI integration. RAM overcommit diagnostic only.
>223 full pytest PASS, frozen baseline unchanged.
> PID1 монтирует SD RO, actual libc paths symlink, genuine picoarch/FrogUI binaries,
> RAM bind-copy frogui/settings.txt с menu_sounds=off (настоящая ветка бинарника,
> не fake sound exports), neutral4B SysV input. Child lifetime8с/process group;
> kill/reap перед report-only RW remount, UI settings/assets/saves на SD не менять.
> Camera нужна только при actual hardware cycle для visual proof, сейчас не открывали.
> Source modes static evidence: plat_init reads /mnt/sdcard/frogui/settings.txt,
> menu_sounds==on вызывает audio, иначе пропускает; не заявлять audible/navigation PASS.
>211 pytest PASS. Конкретную RAM/settings safety ещё принять на устройстве.

> **Последние аппаратные тесты 2026-11-15 (приоритет над историей ниже):**
> пользователь разрешил «тестируй всё на консоли». Связь stock4.4 и6 hashes
> подтверждены перед опытами. Все3 завершённых cold trials вернули stock/MTP
> автоматически, native_restore_verified=true, host_cleanup_wrote_boot_file=false.
> - kernel_cold_display_input_v1_trial.json: display scanout PASS,2 evdev devices
>   present, events0, IRQ ERR2. Только inventory PASS, physical mapping/navigation
>   НЕ подтверждены. Не объявлять все кнопки рабочими.
> - kernel_cold_audio_silent_v1_trial.json: module0, DMA moved, IRQ0->5,
>   gain0/mute1, DROP0/RUN0; frames7016/24576, поэтому silent acceptance FAIL.
>   Пробник исчерпал256 итераций на EAGAIN. Исправлен на monotonic5с deadline,
>   backoff1мс и редкие sysfs snapshots. Новый binary r36-display-audio-silent-probe-v3.
>   **Новая сборка exit0 и fetch PASS:** payload/kernel_audio_silent_vm_v2,
>   kernel_audio_silent_active_v2; exact ALSA12word UAPI matched,29 imports verified.
>   Cold wrapper kernel_cold_audio_silent_v2 hardware finished and returned stock:
>   DMA moved/IRQ0->41/gain0/mute1/DROP0/RUN0; frames24672 вместо24576, strict
>   acceptance FAIL. Исправлена последняя запись min(remaining,512), исходник
>   audio_probe.h обновлён. **Silent v3 HARDWARE PASS:** kernel_cold_audio_silent_v3
>   trial audio_acceptance=true,24576frames/IRQ0->41/DMA moved/gain0mute1/DROP0/RUN0.
>   Stock/native restore/watchdog6hashes PASS, no host cleanup writes. Кандидат
>   kernel_audio_silent_active_v3 сделан reversible init-only patch от v2 (source
>   unchanged, module ABI matched). Audible/amp/headphone НЕ проверены.
> - kernel_cold_usb_cdc_v1_trial.json: kernel/PID1/SD PASS, gadget FAIL ENOENT
>   phase=acm_function, Windows CDC не появился. Root cause: configfs kern_path
>   разрешает symlink target от syscall cwd. Absolute target fix + acm_link phase
>   добавлены usb_cdc_init.c, test syscall-model проверяет exact absolute path.
>   USB fix пересобран kernel_usb_cdc_vm_v3/coldUSBv2: hardware device bound,
>   UDC configured/unbind0, но pings0 и host matcher FAIL. Windows cache exact
>   PnP USB VID1D6B PID0104 serialR36LAB-CDC-DIAG COM12 найден. pyserial может
>   терять serial с дефисами; usb_windows_identity.py проверяет PresentOnly exact
>   instance/StatusOK, watch tool использует только этот порт. Не считать cached
>   COM текущим. v3 host watcher упал на PowerShell query timeout; device снова
>   configured/pings0, stock return PASS. Перешли на прямые cfgmgr32 devnode
>   NORMAL+DN_STARTED и registry PortName, без PowerShell/poll-stall.
>   **USB CDC v4 HARDWARE PASS:** kernel_cold_usb_cdc_v4_trial.json +
>   usb_cdc_host_hardware_20261115_v4.json: exact present COM12,3random PING/PONG,
>   device114rx/114tx/3pings,bind/unbind0. Watchdog/native restore6hashes PASS,
>   no host cleanup writes. USB_CDC_HARDWARE_VERIFIED.json. MTP/host/OTG/background
>   не приняты. Все raw прежние fail reports сохранены.
> - stock_core_smoke_20261115_v1 failed BEFORE core: diagnostic harness wanted
>   GLIBC2.34. Сохранены actual libc/libdl/loader в console_runtime_20261115_v1;
>   console_glibc_compat.h + linking actual runtime produced libretro-smoke-console-v2
>   without GLIBC2.34. Stock smoke v2 Gambatte/FCEUmm PASS на real CPU/stock libs,
>   synthetic ROM120frames/input/PCM/savestate; это НЕ Linux7 acceptance.
> - Linux7 core candidate готов и software/fallback PASS:
>   payload/kernel_cold_core_console_v1, source kernel_core_console_v1. Frozen
>   kernel CODE unchanged, только initramfs patched+display reservations; exact
>   profile validation passed. Extras r36-libretro-smoke-console и original
>   synthetic GB/NES. Child uses /sd/rootfs/lib/ld.so.1 + actual SD libraries,
>   RAM working dir, bounded8с per core. **На Linux7 actual console PASS:**
>   kernel_cold_core_console_v1_trial.json core_acceptance=true, Gambatte/FCEUmm
>   120frames/nonzero callbacks/input/savestate. Watchdog-return/6hashes native
>   restore PASS, no host cleanup writes. Это headless, НЕ physical gameplay/UI.
> - console_acceptance_20261115.json содержит текущие частичные результаты.
>   Следующие шаги: полный picoarch/FrogUI bootstrap и связка backend,
>   physical key calibration/IRQERR2, audible/amp/headphone, MTP/host integration.
>   Не повторять old trial IDs. Пока headless cores/silentDMA/videoABI/CDC —
>   отдельные accepted slices, НЕ полная совместная UI/game приёмка.
> - Real glibc video backend/harness пересобраны против actual saved console
>   runtime (including libpthread), без GLIBC2.34: driver_r36_drm_console_v1.so,
>   frontend-backend-console-v1. Isolated static frontend_console_init.c loads
>   matching DRM module, runs child via actual SD loader, bounded8с.
>   kernel_cold_frontend_backend_v1 hardware FAIL: real module0, glibc backend
>   init ENOMEM12, child exit1. Stock watchdog-return/6hashes restore PASS.
>   v2 pinpoint phase=connector. Root cause missing initial mode-count probe,
>   not proven RAM exhaustion (stale errno). Added zero-count GETCONNECTOR then
>   proper props buffers. **v3 HARDWARE BACKEND PASS:**
>   kernel_cold_frontend_backend_v3_trial.json, actual SD glibc/runtime,
>   driver_r36_drm_console_v3.so,60frames via video ABI, child0/module0,
>   watchdog/native restore6hashes PASS. Full picoarch/FrogUI ещё НЕ проверены.
> - VM USB source build завершён/fetched. Не запускать параллельно другие source
>   builds. Остальные кандидаты init-only
>   patches в НОВЫХ папках с hash reversal checks; baseline не меняется.

> **Офлайн USB/video integration 2026-11-14:** консоль/COM/MTP/камера/микрофон
> НЕ использовались. usb_overlay.py убирает только Linux IRQ-depth enable/disable
> callbacks и trailing disable_irq после child registration: musb_stop зовёт
> platform_disable под musb lock, synchronizing disable_irq там опасен; core
> сам маскирует device IRQ. Контракт optional callbacks проверен в musb_core.h.
> Hardware causal claim отсутствует. Изменение только private integrate overlay.
> Isolated USB build --usb-probe запущен в owned VM: r36-usb-cdc.dts,
> usb_cdc_init.c static MIPS binary-v1. Только USB0 peripheral/PIO, usb1 disabled,
> без UART/audio/input/host/OTG/MTP/mass-storage. CDC12с окно, watchdog не кормится,
> unbind+SD report. Host usb_cdc_host.py требует явный COM с точными VID/PID/serial,
>3 случайных PING/PONG32hex, bounded IO; ничего не перечислялось/не открывалось
> в этой сессии. fetch_usb_build.py проверяет точную allowlist/config/ELF/initramfs.
> Первый USB build exit0 отвергнут isolation preflight (INPUT via TTY->VT);
> payload/kernel_usb_cdc_vm_v1/VALIDATION_FAILED.json, НЕ использовать.
> USB profile теперь EXPERT=y/VT=n/HID=n/INPUT=n, assertion до compile.
> **Финальный offline build PASS exit0/preflight:** payload/kernel_usb_cdc_vm_v2,
> build_receipt.json. Kernel SHA25694684c56a72ab07d7fc1d5a53937905fce4b1fa14027a732b3da87cea2fc1b43.
> Static init/hash/ELF/initramfs/gadget-only isolation и фактический glue source
> проверены. hardware_verified=false/deployed=false.
> **USB cold wrapper 2026-11-15 offline PASS:** payload/kernel_cold_usb_cdc_v1,
> OFFLINE_VERIFIED.json. Candidate SHA256a9e836992ad0e8c363a1d9d5d34500f33e874a7b3332bd00832f39843337ebb0,
> tag0xc840b04c, entry0x805446b4, inlineDTB0x80714000, watchdog30с.
> Native bootm/header/CRC/gzip PASS;8 cold success/fault paths +1 native-decrypt
> fallback PASS. Реальный kernel head достиг start_kernel. File APIs stubs,
> USB/MMIO/SD на железе НЕ эмулируются.193 full pytest PASS,62 frozen hashes
> неизменны. Ничего не установлено, COM/MTP/камера/микрофон не открывались.
>
> **Эмулятор->новый backend офлайн PASS:** emulator_backend_smoke_v1/suite.json,
>4 unchanged MIPS cores x press-release/neutral x120 frames через настоящий код
> video_drm_backend.c и scaler. Только DRM ioctls/device modeled в test library
> driver_r36_test_mockdrm_v1.so; production library этим НЕ подменяется.
> libretro_video.h корректно converts1555/8888/565->RGB565 (pitch/bounds tests).
> libretro-smoke-mips-v5 + test backend actual_backend_frames120 каждый case,
> save-state/input/video/PCM PASS. Не physical DRM/UI/performance acceptance.
>189 full pytest PASS. Все32768 colors1555 conversion tested. Production backend
> missing-DRM negative control PASS: emulator_backend_negative_v1.json (exit1,
> no false success). Финальный USB build/preflight PASS, hardware USB ещё pending.
> Frozen working
> display/kernel_ready не менять. USB_PORT_STATUS.ru.md содержит deferred acceptance.

> **Единая очередь оставшегося переноса и испытаний:**
> analysis/driver_port/REMAINING_AND_TESTS.ru.md (2026-11-14).
> Пользователь дополнительно подтвердил: USB обязательно переносить, не забывать
> за UI/audio/input/emulators. MTP после watchdog-return — stock4.4, НЕ новый USB.
> Пункты checklist не выполнены, если явно не подтверждены отчётами. Консоль
> пока недоступна, hardware/audio tests отложены; не опрашивать MTP по кругу.

> **Текущая задача пользователя, 2026-11-14:** консоль пока подключить невозможно.
> Аппаратную проверку звука ОТЛОЖИТЬ и сохранить как задачу. Не опрашивать MTP,
> не запускать boot/upload/микрофон или камеру без необходимости. Продолжать
> локально кнопки и эмуляторы. Звук: после подключения сначала passive ownership,
> затем kernel_cold_audio_silent_v1 + watchdog, только после silent PASS короткий
> тон/микрофон/amp/headphone. Подробности в analysis/driver_port/AUDIO_TEST_TODO.ru.md.
>
> **Офлайн кнопки/эмуляторы 2026-11-14:** без MTP/камеры/микрофона/консоли.
> legacy_keys.c теперь восстанавливает held-at-start через EVIOCGKEY;
> новый static MIPS analysis/driver_port/r36-legacy-keys-v3. Native Linux
> uinput->evdev->SysV8 scenarios PASS: keys_evdev_sysv_integration_v3.json.
> MIPS publisher через QEMU-user пока НЕ accepted: EVIOCGID ENOTTY на host evdev;
> это не physical hardware failure, не обходить ioctl-проверку ради PASS.
> Full chain native publisher + real shared SysV + MIPS Gambatte + synthetic ROM
> PASS (11 scenarios): keys_core_integration_v1.json. ROM сам увидел press/release.
> calibrate_legacy_keys.py требует HUMAN physical labels->event ordinals в свежем
> capture, rejects duplicate/no-release/dropped/stale, пишет explicit map. Никакой
> physical serial ordering пока НЕ подтверждено.
>
> ЧЕТЫРЕ unchanged cores Gambatte/Gearboy/FCEUmm/QuickNES реально исполнились
> в MIPS QEMU74Kf: по120 frames в press-release и neutral control, nonzero video
> и PCM callbacks, RAM signature42/press/release, serialize->mutate RAM->unserialize
> restore PASS.8 cases report analysis/driver_port/emulator_smoke_v3/suite.json.
> Harness libretro-smoke-mips-v3 (v4 добавляет actual SysV mode). Synthetic original
> GB/NES programs сгенерированы make_synthetic_roms.py; no commercial content,
> BIOS/user ROMs не копировались. Никаких claims по speed/real games/hardware.
> Runtime из existing Debian MIPS libs + libstdc++ от btbundle, НЕ actual console libs.
>173 full pytest PASS. Verified DRM candidate/frozen62 artifacts не менять.

> **Audio silent bring-up подготовлен 2026-11-14, НЕ ЗАПУЩЕН НА КОНСОЛИ:**
> пользователь разрешил слышимый сигнал и микрофон. MTP несколько read-only
> попыток подряд отсутствует; новых upload/boot/микрофон-записей не делали.
> Source audio_driver_source_v3: refuses existing RUN DMA before hw_init,
> health sysfs, gain0/mute=true, no foreign syscore. .r36audio exact UAPI12 words
> совпали probe/module (hw604/sw104/xfer12/info288 and actual MIPS ioctl values).
> Probe scripts/peripheral_lab/audio_probe.h compiled into
> analysis/driver_port/r36-display-audio-silent-probe-v2. Real ALSA48k/S16LE/stereo,
>24576 silent frames, must see DMA movement/IRQ increase, DROP success and RUN0.
> No tone/amp GPIO writes. Kernel built/fetched kernel_audio_silent_vm_v1,
> all29 module imports verified. prepare_audio_probe_variant.py created
> kernel_audio_silent_active_v1 (only audio okay; display/RPC disabled), cold
> kernel_cold_audio_silent_v1 software/fallback оба PASS. Полный pytest163 PASS
> (один старый test сначала упал из-за чужого KMS fixture, исправлен на вариант
> от текущего candidate; production проверки не ослаблялись).
> audio_result parser added to cold trial collection; silent PASS never means
> audible PASS.16 focused tests PASS. For hardware first restore MTP, run passive
> stock audio snapshot r36-audio-passive-v1, confirm ownership before silent test.
> Current active module opt-in still changes shared audio clocks/reset: only
> deliberate isolated watchdog cycle, not stock runtime module load.

> **Следующий перенос frontend/input/audio 2026-11-14:** новый статус
> analysis/driver_port/FRONTEND_PORT_STATUS.json. ПРЕЖНИЙ UI/эмуляторы НЕ запущены.
> - Статически подтверждена обязательная video ABI тройка picoarch:
>   video_drivers_init(void) -> positive, video_driver_disp_frame(src,w,h,pitch),
>   video_driver_deinit. PICOARCH_DRIVER override существует; audio loader отдельный.
> - Реальная новая library scripts/peripheral_lab/video_drm_backend.c,
>   analysis/driver_port/driver_r36_drm_video_v2.so (MIPS glibc/hard-float, max GLIBC2.4),
>   CPU RGB565 scaling/letterbox/DRM, no fake g_render/GE/sound exports. Host mocked
>   real-code DRM test PASS; MIPS glibc dlopen+fail-closed PASS. Hardware library
>   submit/старый picoarch пока НЕ проверены. Single buffer, possible tearing;
>   failed restore/disable retains scanout allocation rather than freeing live DMA.
> - scripts/peripheral_lab/legacy_keys.c + legacy_keys.h: evdev->4B SysV
>   ftok(/tmp/joy_key,'a'), explicit calibrated code->bit map, exclusive publisher,
>   OR of independent source states, SYN_DROPPED fail-closed. Static MIPS v2 built;
>   mapping/hardware navigation НЕ проверены.
> - Isolated input DT scripts/kernel_lab/r36-display-input.dts uses poll-only
>   GPIO2/7/11 and serializer clock8/data9. Raw BTN_TRIGGER_HAPPY1..12 positions,
>   no claimed physical mapping; pins0/1/3/4/5/6/19 НЕ трогаются.
>   kernel_display_input_vm_v1 / kernel_display_input_kms_vm_v1 собраны; cold
>   kernel_cold_display_input_v1 software/fallback PASS. Hardware attempt FAILED
>   на первом preflight: MTP unavailable, ДО upload/boot changes. Receipt не создан,
>   потому что связь отсутствовала до него. Никаких reset в этом опыте не было.
> - Staged native ALSA source payload/audio_driver_source_v1; без foreign syscore,
>   gain0/mute=true, DT disabled, module allow_takeover=false. Реальная PCM/IRQ/DMA
>   часть, не dummy audio. AmpGPIO19/headphone15 ownership остаётся блокером.
>   Первая VM audio build FAILED at modpost: snd_pcm_new/set_ops/period_elapsed
>   и др. undefined; hidden CONFIG_SND_PCM удалён olddefconfig. Добавлен visible
>   SND_R36_EXTERNAL_DEPS selecting PCM + assertion before build. Повторный build
>   запущен; пока не объявлять built/hardware PASS. VM date корректируется из
>   host перед tar extract для clock-skew предупреждений; WSL kernel не трогается.
>   Повторная сборка **PASS exit0**: payload/kernel_display_input_audio_vm_v1,
>   build_receipt.json проверен (all28 audio imports exported, MIPS vermagic/hash).
>   Kernel SHA256512928e1f1c09956f8e059ee257f983aa11854874fcfaa7fd7f217753fdb29f9;
>   audio .ko b6adbf798deb6fab57c15eafc1973be5ac6053b11b6cd5c01c6704e460fab200.
>   Audio DT disabled, hardware_verified=false, ничего на консоль не установлено.
> - Изменены только наши scripts/analysis/new payload, companion UI repos не менялись.
> 144 full pytest PASS, затем новый audio-archive opt-in focused suite16 PASS.
>   Последний full pytest147 PASS. frontend_saved_runtime_v1.json: локальная
>   сохранённая rootfs неполна (нет libc/loader/libdl/libm/libfreetype и др.);
>   actual console userspace надо проверить до первого UI launch. Не заменять
>   отсутствующие библиотеки новыми системными без проверки ABI.
>   frontend_compat_build_v1.json фиксирует hashes backend/harness/keys/audio-inspect.
>   Hardware harness ещё НЕ запущен. Новые source checks SYN_DROPPED в input_probe.h
>   добавлены после frozen input binary-v1; для них нужен новый binary/candidate,
>   не выдавать существующий v1 за пересобранный.
>   Для продолжения hardware пользователь должен вернуть MTP; два последних
>   read-only preflight показали R36S not found. Рабочий display candidate не менять.

> **Аппаратные опыты 2026-11-14 (новее записей ниже):** пользователь разрешил
> тесты с watchdog-откатом и локальную веб-камеру. Пассивный display опыт
> `analysis/boot_crypto/kernel_cold_display_passive_v1_trial.json` PASS:
> Linux7.2-r36disp/PID1/SD, timing/header/raster PASS, watchdog30с вернул stock,
> MTP вернулся, все6 hashes исходные до host cleanup, host boot writes=false.
> KMS v1 тоже автоматически вернул stock, но display FAIL: module load0,
> platform probe -EINVAL panel-timing. Найдено: of_get_drm_panel_display_mode
> требует width-mm/height-mm, которые отсутствовали. Добавлены0/0 (unknown,
> не выдуманные размеры) в новый display_driver_source_v4.
> Новые kernel_display_vm_v3 / kernel_display_kms_vm_v3, cold wrapper
> kernel_cold_display_kms_v2 прошли offline/fallback. Его hardware trial сейчас
> завершён: kernel_cold_display_kms_v2_trial.json подтверждает watchdog30с возврат,
> MTP и все6 stock hashes без host cleanup writes. DRM card0 зарегистрирована,
> panel-timing исправлен, но probe_rc=-1/errno14 до modeset. Исправлены userspace
> connector props/values arrays (после count query count_props nonzero, раньше
> pointers0 давали EFAULT) и 64-bit off_t для DRM mmap offsets. Добавлены checked_ioctl
> stage logs. Новый binary analysis/driver_port/r36-display-probe-v2;
> kernel_display_vm_v4 / kernel_display_kms_vm_v4; cold kernel_cold_display_kms_v3
> аппаратно: version/resources/connector/create/map/addfb/setcrtc/wait_vblank rc0;
> active descriptor02f90400, pixels01500000/RGB565/640x480/pitch1280, timing stable,
> flip_timeouts0. Финальный PASS отсутствует: IRQ before/after check отказал до
> pixel hash. Камера пересвечена, полосы НЕ подтверждены. Watchdog вернул stock,
> MTP восстановился, все6 hashes исходные без host cleanup writes.
> KMS v4 (kernel_display_kms_vm_v5 / r36-display-probe-v3): второй WAIT_VBLANK
> rc0, но IRQ before=after0; /proc/interrupts display40=0 и mmc10=0, ERR0.
> Камера с exposure-6 **подтвердила цветные полосы** и возврат штатного меню:
> analysis/driver_port/display_visual_kms_v4.json + private local frames.
> Полный scanout PASS всё ещё false (hash stage не достигнут).
> Найдена причина accounting: handle_percpu_irq не увеличивает tot_count,
> Linux7 proc.c показывает device IRQ0 при tot_count0. integrate_ports.py
> заменяет только SoC mapping flow на handle_simple_irq (ack остаётся device).
> **KMS v5 IRQ-fix аппаратно PASS:** kernel_cold_display_kms_v5_irqfix,
> source kernel_display_kms_vm_v6_irqfix; scanout PASS, IRQ2->18, MMC213, ERR0,
> CPU/DMA pixel hashes8d21d5c5 совпали. Локальная камера подтвердила стабильные
> цветные полосы и возврат stock меню. Авторитетный итог
> analysis/driver_port/DISPLAY_HARDWARE_VERIFIED.json; подробный trial
> analysis/boot_crypto/kernel_cold_display_kms_v5_irqfix_trial.json.
> Все завершённые cold trials вернули stock/MTP без host boot writes,6 hashes
> оригинальные. Это fixed640x480 bring-up, не full UI/audio/input/power-cycle PASS.
>137 pytest PASS, frozen62 files hashes неизменны. Рабочий кандидат не менять.
> Ранний fsck RAM комплект staged payload/fat_guard_ramfs_staged_v1 (НЕ kernel,
> НЕ установлен): статические init/next-init/guard/fsck. Production writer по
> умолчанию disabled. Read-only стадия теперь НЕ выключает watchdog; выключение
> возможно только непосредственно перед будущим разрешённым writer.
> Локальные кадры без аудио: analysis/driver_port/camera_kms/kms_v1_*.jpg,
> kms_v2_*.jpg. Не публиковать кадры.
>
> **Авто-fsck — подготовка, НЕ установлен:** пользователь хочет проверку и ремонт
> после нештатного выключения на самой консоли до mount. Старый static glibc
> fsck не имеет автономного CP437, rc1 смешан с fatal, fs_flush скрывает write errors.
> `scripts/kernel_lab/prepare_boot_fsck.py` создаёт новый patched source tree
> (исходный архив hash проверяется): internal CP437, fatal8, fsync before close,
> финальный R36_FSCK_COMPLETE_V1 marker после успешного fs_close.
> Готовое staged дерево modbuild/boot_fsck_stage_v2/dosfstools-4.2,
> WSL build /root/r36-boot-fsck-build-v2b. WSL исправно работает; kernel source не менялся.
> Бинарники analysis/driver_port/r36-fsck-cp437-v2, r36-mkfs-cp437-test-v2
> (mkfs только для тестовых regular images, не консоли!), r36-fat-boot-guard-v2.
> fsck MIPS QEMU: clean/dirty/orphan/loop/invalid PASS,
> отчёт fat_fsck_images_v2.json. Все255 CP437 chars roundtrip+buffer bounds PASS.
> Guard требует полный marker+rc0/1; 8 process tests PASS в Linux host+MIPS child,
> отчёт fat_guard_process_tests_v2.json. qemu-user не умеет exec MIPS child без
> binfmt, поэтому native guard использовал test-only wrapper, это не native
> MIPS fork/exec hardware acceptance.
> **Production repair в fat_boot_guard.c намеренно заблокирован**, guard не встроен
> в initramfs. Отключение watchdog на writer пока не испытано; нельзя обещать
> одновременно принудительный30с rollback и безопасный fsck writer.
> Нужны RAM/geometry guard, интеграция PID1 ДО mount, сохранение отчётов/metadata,
> аппаратная read-only проверка до разрешения writer. Не ставить старый sdfix.sh
> с -w и не запускать fsck на mounted SD. Последний pytest132 PASS.

> **Продолжение после OpenCode, 2026-11-13:** прочитана последняя локальная сессия
> OpenCode `ses_e3cadd4d2ffefHkExAjgIO84To` из opencode.db (read-only).
> Она остановилась на display_driver_source_v3 / повторной DRM-сборке и MIPS selftest.
> Сохранённая QEMU VM возобновлена; WSL теперь Running и отвечает, но не использовалась
> для сборки и её source tree не менялся. Консоль в этом продолжении не трогали.
>
> Реальный `qemu-mipsel -cpu 74Kf` selftest: PASS/exit0, pattern_hash8d21d5c5,
> corrupted_hashce643dc4, padding_preserved1. Отчёт
> `analysis/driver_port/display_qemu_selftest_20261113.json`. Это userspace pattern
> test, не эмуляция HC16xx display/IRQ/AVP.
>
> После остановки VM на диске были нулевые archive/exit и stale0B DRM .o. Первый
> повторный комплект **отклонён**: `payload/kernel_display_vm_v1/VALIDATION_FAILED.json`.
> Не использовать его. В vm_build_kernel.sh добавлены clean внешних модулей,
> gzip verification и sync до объявления успеха. Повторная чистая сборка прошла.
>
> **Проверенный offline build:** `payload/kernel_display_vm_v2/build_receipt.json`:
> Linux7.2.0-rc5-r36disp #7, SHA256b694948abe6fdb75c55507d9358b5dd417dadad97b38d8d944e5b4ac4178d20a.
> DRM module SHA256963e2b4c38d4b273a6fa184f680729bd4c82a384eca24d916de7e004131627a8;
>110 imports найдены в exports этого kernel, probe/module MIPS DRM ioctl ABI совпали,
> initramfs/ELF/flat/DT/source provenance проверены. Hardware_verified=false.
> Пассивный профиль: display/RPC disabled, --display-kms-probe отсутствует.
> `payload/kernel_display_kms_vm_v2` — отдельный НЕУСТАНОВЛЕННЫЙ KMS-кандидат,
> display okay, RPC disabled, extra r36_hc16xx_drm.ko, explicit init argument.
> KMS-испытание/визуальный экран/старый UI не запускались.
>
> Новый проверяющий fetcher: `scripts/peripheral_lab/fetch_display_build.py`.
> Последний общий прогон:130 pytest PASS (kernel_lab+peripheral_lab+crypto с реальным
> display candidate). В cold trial добавлены сбор display report и строгая приёмка
> fresh/release/completeness/hash/IRQ/raster с разделением passive/KMS. Физическая
> панель не объявляется проверенной. Log: `analysis/kernel_build_vm_v1/display-build-verified-v2.log`.
> Подготовлена cold-обёртка **только пассивного** профиля:
> `payload/kernel_cold_display_passive_v1`; native bootm/header/gzip PASS,
> cold_restore_emulation.json PASS (8 success/fault scenarios, real kernel head
> reached start_kernel), cold_restore_native_fallback.json PASS (original decrypt).
> File APIs в этих эмуляциях — stubs, не реальная SD. Все62 frozen artifact hashes
> проверены и неизменны.
> Ничего на SD/NOR не устанавливалось. До hardware нужен доступ к консоли и
> согласование загрузочного опыта; прежнее ограничение «Пока без консоли» сохранено.
>
> При повторном запуске VM старый overlay прервал bootstrap на повторном modloop
> start. Существующий ext4 vda подключён без форматирования, инструменты/SSH
> восстановлены; `build_vm.py --refresh-overlay` обновил overlay для будущего запуска.
> VM оставлена работающей, state.json содержит текущие PID/пути. Не завершать её
> принудительно: сначала дождаться сборки и выполнить sync/корректный poweroff.

> **Последнее продолжение — подготовка периферии, hardware отложен пользователем.**
> На запрос «UI/экран/звук/кнопки» снят stock ABI inventory и создан первый AVP
> polling client + kernel diagnostic `scripts/kernel_lab/amprpc_driver/r36_amprpc_poll.c`.
> Пользователь выбрал «Пока без консоли»: после этого новые образы не устанавливались.
> Полностью собраны kernel7.2.0-rc5-r36port иr36_amprpc_poll.ko в отдельной
> QEMU/WHPX Linux VM, WSL ubmips StopPending не перезапускалась.
> `payload/kernel_port_avp_vm_v1/build_receipt.json`: build_passed=true,
> SYSVIPC=true, ELF/vermagic/последний init проверены; hardware_verified=false.
> Текущие cold artifacts: kernel_cold_avp_probe_v3 (isolated frozen code),
> kernel_cold_port_avp_vm_v1 (rebuilt user polling),
> kernel_cold_port_avp_module_vm_v1 (rebuilt kernel-module mode).
> Все прошли software bootm/gzip/real kernel head и fallback checks, но RPC response
> на AVP не принят. UI/экран/звук/кнопки наLinux7 по-прежнему не готовы.
> План/ABI/порядок тестов: `analysis/driver_port/UI_PORT_PLAN.ru.md`;
> фактические статусы: PORT_MATRIX.ru.md. До продолжения hardware нужен доступ к консоли.
> VM state/SSH key paths только в analysis/kernel_build_vm_v1/state.json;
> source/build находятся в /work гостя. Есть работающий clang20+GNU MIPS as2.44,
> modules_prepare обязателен. Не редактировать/не перезапускать чужую WSL.

> **Самое новое, аппаратно подтверждено 2026-11-13:** Linux7 запущен напрямую из
> NOR после hardware watchdog-reset, без RAM-handoff и запуска stock4.4 перед ним
> в этом цикле. Candidate `payload/kernel_cold_early_restore_v1`, SHA2562da0c4016a9aa356bc6ddc2d195dd5866707c6378bc85f0b23e2ae99c839948b.
> Stage6/tag0xc5d28f11, run_idaa8961f5e8fd47cdabb0a2dc3081efa7, release7.2.0-rc5-r36lab#12/pid1/SD proof.
> Раннее восстановление подтверждено отдельным stamp, watchdog вернулstock,
> все6 boot hashes исходные, host_cleanup_wrote_boot_file=false.
> Авторитетный аудит: `analysis/boot_crypto/kernel_cold_early_restore_v1_trial_VERIFIED.json`.
> Детали: `analysis/boot_crypto/COLD_BOOT.ru.md`. Power-off/on, cold module test,
> экран/звук/кнопки/TreeFrogUI на Linux7 остаются отдельными задачами.
> Ниже сохранены исторические этапы; старые утверждения «Linux7 cold boot ещё нет»
> больше не относятся к NOR-reset испытанию. Frozen bundle не менять.

> **Последний аппаратный результат 2026-11-13:** early restore действительно
> восстановил advapi32.dll ДО Linux. Receipt
> `analysis/boot_crypto/kernel_loader_early_restore_probe_v1_trial.json`:
> stage202/tag0xbd6eb903, source/readback CRCc3693b14,3954299B,
> stock_already_restored_before_host_cleanup=true, host_cleanup_wrote_boot_file=false.
> Проверены также watchdog pending-skip и полная sandbox copy. На консоли stock4.4.
> См. `analysis/boot_crypto/EARLY_RESTORE.ru.md` перед следующей правкой:
> probe error branch пока использует встроенный stock kernel; интеграция Linux7
> требует своего корректного stock fallback, а не прыжка по старому entry.

> **Актуально 2026-11-13:** cipher полностью восстановлен (ChaCha20), реальные
> boot-алиасы подтверждены: advapi32.dll/Bubbles.scr/ApplicationFrame.dll.
> Неудачный прямой Linux7-тест восстановлен через кардридер; stock4.4 и hash
> подтверждены на консоли. Затем stock-bridge-зонд аппаратно выполнился после
> NOR-reset: stage193/tag0xa1227d68, MTP вернулся, оригинал advapi восстановлен.
> `analysis/boot_crypto/stock_bridge_trial.json`. Это НЕ холодный старт Linux7.
> Найдена условная несовместимость shim по0x80000000 с boot-wait чтением u16
> по physical0x2; исправленный отдельный кандидат `kernel_direct_advapi_lowram_v3`
> имеет entry0x80010000 и не установлен. Точная стадия старого сбоя неизвестна:
> RAM-журнал утрачен после выключения. См. актуальный `analysis/boot_crypto/STATUS.ru.md`.
> Старые утверждения ниже о неизвестном cipher/непроведённом ремонте — история.

> **Обновление после первоначального handoff:** исследование шифрования продолжалось,
> временный capture-DTB не дал MTP и уже откатан. Карта затем прошла реальный
> CHKDSK в картридере; потерянная цепочка16KiB сохранена, повторная проверка чистая.
> Полный backup16-ГБ раздела теперь есть. Актуальные сведения:
> `analysis/boot_crypto/STATUS.ru.md` и
> `analysis/fat_repair/reader-20261112-231822/verified_repair.json`.
> Раздел8 ниже описывает состояние **до** этого ремонта, а не текущую незавершённость.

## 1. Сначала прочитать

Рабочий каталог Windows: `D:\r36s-`. Верхний уровень теперь локальный
Git-репозиторий (инициализация и актуальные коммиты разрешены пользователем).
Правила: AGENTS.md, раздел Keep Git Current. Сторонние проекты, payload/dumps,
секреты и generated files не добавлять. Не push без отдельного запроса.
Общаться с пользователем по-русски, сообщать о проверенных результатах.

**Последняя цель пользователя:** вся консоль должна работать на собственном ядре,
с прежним интерфейсом, звуками и кнопками. Пользователь также явно разрешил
ремонт файловой системы. Затем попросил остановиться и передать работу другому агенту.

**Ключевое достижение:** наше ядро Linux7.2.0-rc5-r36lab реально загружается на
консоли, выполняет свой PID1, пишет proof на SD; собственный внешний `.ko`
загружается, проверяется и выгружается. Два цикла прошли автоматически,
watchdog вернул штатный Linux без ручных перезапусков.

**Не сделано:** ремонт FAT ещё НЕ запускался; полный перенос периферийных
драйверов не завершён; новая ОС пока не запускает игровой интерфейс.

## 1.0. Перезапуск ПК по запросу пользователя, 2026-11-13

Пользователь попросил перезагрузить ПК и снова открыть это окно. Перед этим
проверено: LxssManager всё ещё StopPending. Попытка завершить PID19180
от LocalSystem через одноразовую задачу тоже вернула Access denied;
факт SYSTEM и ошибка сохранены в `analysis/wsl_system_recovery.log`.

Для открытия проекта после входа планируется одноразовая запись Windows RunOnce
`R36ResumeVSCode`: VS Code + `D:\r36s-` + этот handoff. Она не гарантирует
автовосстановление конкретной вкладки чата. После перезапуска проверить
`wsl -d ubmips -- true` с ограничением времени и продолжить перенос драйверов.
Не запускать repair/boot вслепую; состояние консоли могло измениться.

## 1.1. Продолжение 2026-11-12 после handoff

Цель пользователя подтверждена: перенос старых драйверов, прежний интерфейс,
эмуляторы и звук на свежем ядре. В этом продолжении новых boot/ремонта FAT не было.
Frozen `payload/kernel_ready` не изменён.

- Пользователь через вопрос разрешил восстановление WSL с остановкой его процессов.
  `LxssManager` всё ещё StopPending, PID19180; процесс обслуживает только эту службу.
  Обычный start получил Access denied; **elevated** recovery также получил отказ
  taskkill. Сценарий `scripts/kernel_lab/recover_wsl.ps1`, журнал
  `analysis/wsl_recovery.log`. По следующему прямому запросу пользователя выполнена
  также одноразовая задача от LocalSystem (SID S-1-5-18): taskkill PID19180 снова
  получил Access denied. Журнал `analysis/wsl_system_recovery.log`; созданная задача
  удалена, подтверждение `analysis/wsl_system_task_cleanup.log`. Служба осталась
  StopPending. Windows не перезагружали; вероятно, нужна её перезагрузка.
- Живая read-only проверка stock:4.4.186 #23, uptime2924.06 в снимке,
  все7 SD aliases RW, swap131068KiB/used12KiB. USB/MTP исправны.
- Начат реальный перенос чистой register-логики AMPRPC:
  `scripts/kernel_lab/ports/amprpc-mailbox-plan.h`; **ещё не platform driver**,
  не подключён к MMIO/IRQ и не собран MIPS-компилятором. Нужны memory barriers,
  bounded polling, work queue/lifecycle/cache и AVP ABI.
- `scripts/kernel_lab/emulate_amprpc.py` исполняет настоящий stock ISR в Unicorn74KF,
  с synthetic W1C MMIO и stub work queue:13 сценариев PASS.
  `analysis/driver_port/amprpc_isr_emulation_20261112.json`.
- C planner скомпилирован host GCC;24 сравнения против настоящего ISR PASS.
  Полный последний pytest:77 passed, в том числе4 frozen-candidate preflight.
  Команда из Git Bash:
  `R36_TEST_CANDIDATE=D:/r36s-/payload/kernel_ready/driver python -m pytest D:/r36s-/scripts/kernel_lab/tests -q --tb=short --basetemp=D:/r36s-/analysis/NEW_UNIQUE_TEST_DIR`
  Basetemp должен быть новым: pytest может удалять существующий указанный каталог.
- Новый read-only `scripts/kernel_lab/amprpc_inspect.py` снял RAM-таблицы и8 слотов
  стока: `analysis/driver_port/amprpc/1794501998987075900/`. IRQ66, TX bitmap0x0f,
  slot bitmap0xff, pool0xa21d8000..0xa21df000. Таблицы до/после совпали; снимок
  **не атомарный**, свободные слоты содержат устаревшие данные. Никаких AVP запросов
  и mailbox MMIO reads/writes не делалось. Запускать `python scripts/kernel_lab/amprpc_inspect.py`.
- Подробные новые выводы ISR/callback, ограничения и следующий шаг добавлены в
  `analysis/driver_port/AMPRPC_NOTES.ru.md`.
- Ранее озвученный input-only шаг пока **не реализован**: build WSL недоступен.
  После восстановления: отдельный профиль без USB/UART на minimal baseline,
  input inventory/events в SD proof; frozen baseline не менять. Далее AMPRPC.

Экран/звук/интерфейс под новым ядром по-прежнему **не запущены**. Новое в этой
сессии — проверяемая основа переноса mailbox, не аппаратный успех AVP-драйвера.

## 2. Текущее состояние в момент handoff

Последняя живая проверка:

- USB/MTP и удалённый shell доступны.
- Работает штатный `4.4.186-release #23 PREEMPT Tue Jan 27 16:21:59 CST 2026 mips`.
- Uptime1799.13с в снимке; это историческое значение, не текущий таймер.
- Keepawake PID769 работает, `cubevol` PID595 приостановлен STOP.
- Это временно приостанавливает обработчики кнопок/громкости/сна cubevol.
  Для возврата: `sh /mnt/sdcard/cubegm/r36_keepawake.sh stop`.
- Последняя проверка watchdog в stock: control0, таймер выключен.
  После неё новых arm/boot не выполнялось.
- Swap активен: `/mnt/sdcard/cubegm/pagefile.sys`,131068KiB, занято12KiB.
- SD смонтирована RW сразу в `/media/mmc`, `/mnt/sdcard`, `/lib`, `/usr`,
  `/bin`, `/sbin`, `/etc`. **Ремонтировать её fsck в этом состоянии нельзя.**

Снимок: `analysis/fat_repair/handoff_stock_status.txt`.
До handoff выполнялись только чтение состояния и подготовка локальных файлов;
исправления FAT, remount, swapoff и новый kernel handoff в этом последнем этапе не запускались.

### Блокер сборочного окружения

WSL-дистрибутив `ubmips` сейчас не отвечает. Последняя Windows-проверка:
`LxssManager = StopPending`. `wsl -d ubmips -- true` завис до тайм-аута;
доступ к `\\wsl$\ubmips\root` тоже зависал.
На последней проверке активных wsl.exe/wslhost.exe не показано.

**Службу не перезапускали, WSL не shutdown/terminate:** у пользователя была
параллельная сессия, которая может пользоваться WSL. Согласовать восстановление,
не убивать чужую работу. Консольный USB от этого не сломан и доступен.

## 3. Рабочий замороженный комплект — не менять

Каталог: `payload/kernel_ready/`.

```powershell
python D:\r36s-\payload\kernel_ready\START.py
```

Это **диагностическая приёмка**, не установка прошивки и не ремонт FAT.
Сценарий сначала проверяет stock ABI/boot hashes, доставку и CRC, затем запускает:

1. `boot`: минимальный PID1, SD/vfat, свежий proof с уникальным run_id;
2. `driver`: только после PASS boot — r36hello load/parameter/unload/sysfs removal.

Каждый диагностический запуск получает аппаратный watchdog30с до handoff.
Есть ожидание восстановления MTP с ограниченными повторами. Каждый WPD вызов
в отдельном процессе с тайм-аутом. Нет бесконечного ожидания USB.

Bundle manifest SHA256:
`4d6f77f1cf20637d56940df53fc3975d09780a47c58ea4d5c0eef8623122515a`.

`READY.json` неизменяем и содержит build-time `hardware_acceptance=pending`.
**Аппаратный PASS хранится отдельно:**

- `analysis/kernel_ready_HARDWARE_VERIFIED.json`;
- `analysis/acceptance/1794498370587679900/suite.json`;
- подкаталоги `boot/`, `driver/`: proof, kernel.log, trace.bin, meminfo, interrupts;
- `analysis/acceptance/1794498370587679900/stock_final.txt`.

Не редактировать frozen manifest/инструменты/бинарники для отметки успеха:
их согласованность проверяется по hash. Для следующего кандидата создать другой OUT.

## 4. Точные подтверждённые результаты

Оба профиля — `7.2.0-rc5-r36lab`, load0x80100000, entry0x804e5898,
DTB0x82e00000, UHI a0=0xfffffffe, a1=DTB.

| Поле | boot | driver |
|---|---|---|
| Image SHA256 | fb6552de75904ae38aef46c1df119a22bbf865d9e20bf208f58f65d46c2e35be | 1379d2f14371096b7be96485bb0a0659b0c5aa19012cb81567679c41208aee9d |
| Build | #12 Thu Nov 12 12:12:13 UTC 2026 | #13 Thu Nov 12 12:16:23 UTC 2026 |
| Run ID | 4e1ed63d71b940e38c1a499a70f9cfe8 | 1c8eb81fe0d3453299121817ef9fc926 |
| Destination CRC32 | 0c2f2606 | ce5a479a |
| Trace stage / tag | 6 /0xb9ca87fb | 6 /0x2166766e |
| Свой PID1 и SD proof | PASS | PASS |
| Автовозврат в stock | PASS | PASS |
| Свой .ko | не включён | load0, parameter1, unload0, sysfs removed1, PASS |

Полные исходные строки uname и версии также сохранены в JSON/proof.

Проверены также18 pytest-кейсов отказов и6 эмуляций настоящего relocation-кода
и kernel head в Unicorn MIPS74KF. Проверены contiguous/scattered source pages,
UHI, SP/GP, BSS/DTB и bitflip. При порче страницы CRC не совпадает, kernel_entry
не исполняется, stage225 и ожидание watchdog. Эмулятор не моделирует SoC MMIO/DMA/cache.

В живом новом ядре:

- clocksource MIPS; sched_clock594MHz; timer IRQ активен, ERR0;
- SDXC58.6GiB обнаружена; первый раздел FAT32 читается/пишется;
- перед driver-тестом MemTotal42648KiB, Free37180KiB, Available36108KiB;
- snapshot dw-mci IRQ count0 при успешном I/O — исследовать учёт/режим отдельно;
- RAM stress и прямой подсчёт освобождения каждой старой страницы не выполнены.

Штатные boot-файлы не менялись; их MD5 подтверждены и в последнем handoff-снимке:

```text
vmlinux.uImage f994b5e32dc90c5eec7e4bd965bff8fe
avp.uImage     36cf812151712a8a1ec01911ac03ab74
dtb.bin        9492f590fc2db86694d3fdc52a25c3e4
```

NOR не изменяли. Обычная загрузка своего образа вместо encrypted stock uImage
не решена: нынешний способ — одноразовый RAM handoff из работающего стока.

## 5. Как устроена загрузка и важные исправления

Исходники инструментов: `scripts/kernel_lab/`.
Самостоятельный stock module `r36boot.ko` создаёт `/proc/r36boot` и умеет
prepare/probe/cancel/BOOT. Он выделяет source/control/list/trampoline pages
**вне будущих destination-областей**. В BOOT: watchdog, flush cache,
uncached relocation, CRC32 назначения и переход в kernel_entry.

Стоковый CONFIG_KEXEC выключен. ABI измерен по DWARF штатного dsc.ko:
module320B, name+12, init+208, fops108B, read+8, unlocked_ioctl+32.
Stock cache flush0x8001bcec проверяется по16 байтам сигнатуры.
Не переносить эти адреса на другое ядро/прошивку.

В `.r36.binding` loader записаны его image/DTB/sizes/CRC/watchdog/ABI.
Нельзя подменить kernel.bin/DTB без пересборки loader и preflight.
Probe расположен в последних16B trampoline page; stub344B и не пересекается с ним.
Копируемый asm stub не должен содержать unresolved relocations.

Важные изменения private kernel overlay:

- CPU Count/Compare вместо внешнего HC16xx timer. Старый external driver
  останавливал тот же counter, который использовал clocksource/sched_clock.
  Это реальный дефект, но не доказанная единственная причина прежних зависаний.
- Минимальные профили выключают UART/USB/ADC/GPIO, используют только RAM-console.
- Handoff отсоединяет старый UDC до перехода, чтобы прекратить его DMA.
- После cache flush asm не обращается к старому cached stack.
- CRC проверяется до исполнения нового ядра; ошибка не запускает плохой образ.
- У каждого proof уникальный run_id; старый файл/один разрыв USB успехом не считаются.

Сток CONFIG_MODULE_UNLOAD выключен: загруженный loader нельзя заменить rmmod.
Перед другой версией нужен stock restart; acceptance умеет watchdog-reset для этого.

## 6. Watchdog и сохраняющаяся трассировка

- Counter phys0x18818500, control0x18818504; control0x26.
- Clock gate bit22 в0x18800060; enable очищает бит.
- Измерения187495/188358/187467Hz; используется187500Hz.
- Reload =0-rate*seconds; стандартный diagnostic timeout30с.
- Новое ядро держит watchdog clock как CLK_IS_CRITICAL.
- Задаётся `R36_BOOT_TIMEOUT`5..300 при build_loader; frozen suite30с.

`r36bootctl boot-detached` сначала запускает внешний armer, затем UDC disconnect;
BOOT ioctl повторно заводит watchdog непосредственно перед jump.
Source: `wdt_diag.c`, `r36bootctl.c`, `r36boot.c`.

Trace ABIv2: phys0x02f91000, размер0xe00 (3584B), header64B +ring3520B.
Это последний неполный участок RAM: allocator заканчивается0x02f90fff,
SystemRAM —0x02f91e4f. Сохранение меток после watchdog-reset реально проверено.
Полный power-off может стереть trace.

Основные стадии1/2/3/4/5/6 — loader/relocation/CRC verified/kernel_entry/console/PID1.
Дополнительные33..59 локализуют ранний boot;225 означает CRC failure.

```powershell
python D:\r36s-\scripts\kernel_lab\collect_ramconsole.py
```

Декодер: `trace_format.py`. История: `analysis/driver_port/runs/<tag>/`.
Нельзя применять старый collector v1 с phys0x02d00000/64KiB: это историческая,
перезаписываемая стоком область.

## 7. Сборка: когда WSL снова доступен

Pinned source:
`/root/linux-hichip-da5f1a22ef2ff5c46aa3f750fa10825813970b09` в `ubmips`.
Upstream https://github.com/SiarheiVolkau/linux-hichip,
revision `da5f1a22ef2ff5c46aa3f750fa10825813970b09`.
Кросс-компилятор mipsel-linux-gnu-gcc10.3.0. Root source tree общий для наших
профилей: не запускать параллельные сборки с разными .config.

```powershell
python D:\r36s-\scripts\kernel_lab\prepare_bundle.py --output D:\r36s-\payload\kernel_ready_v2
```

Сборка одиночного кандидата:

```powershell
wsl -d ubmips -- env LAB_PROFILE=boot OUT=/mnt/d/r36s-/payload/kernel_boot_next bash /mnt/d/r36s-/scripts/kernel_lab/build_kernel.sh
$env:R36_KERNEL_OUT = 'D:\r36s-\payload\kernel_boot_next'
$env:R36_BOOT_TIMEOUT = '30'
python D:\r36s-\scripts\kernel_lab\build_loader.py
python D:\r36s-\scripts\kernel_lab\emulate_boot.py D:\r36s-\payload\kernel_boot_next
python D:\r36s-\scripts\kernel_lab\preflight.py D:\r36s-\payload\kernel_boot_next
Remove-Item Env:R36_KERNEL_OUT
Remove-Item Env:R36_BOOT_TIMEOUT
```

Профили сейчас: boot, driver, ports, input, memory. **repair ещё не реализован.**
Default build_kernel.sh — ports, поэтому для базового опыта всегда указать profile.
Не использовать старый run_cycle.py вместо frozen acceptance без проверки его состояния.

WSL1 ранее воспроизводимо зависал при GCC vfork->cc1. В наши команды добавлен
`-wrapper /usr/bin/env`, CC/HOSTCC/LD wrappers; системный compiler не заменён.
Built-in экспортов `vmlinux.symvers` достаточно для тестового внешнего .ko,
не нужно выполнять полную сборку всех in-tree modules ради Module.symvers.
Последний dpkg --audit перед нынешним зависанием WSL был чист.

## 8. Приоритет: офлайн-ремонт FAT, ещё НЕ выполнен

Пользователь явно попросил запуск ремонта. Обнаружен dirty-volume warning;
**повреждение данных пока не установлено**. Warning может возникать из-за нашего
warm handoff от живого RW mount: sync не равен чистому unmount/remount-ro.

Геометрия проверена чтением MBR/VBR:

```text
disk /dev/mmcblk0: 61440000 KiB (~58.6 GiB)
partition /dev/mmcblk0p1: MBR type0x0c, start LBA32, sectors30719744
partition bytes15728508928 (~14.65 GiB), остальные MBR slots пусты
FAT32:512 B/sector,32 sectors/cluster (16KiB),959480 clusters
reserved1392 sectors;2 FAT copies по7496 sectors (3837952 B каждая)
data starts at partition-relative sector16384 =8MiB
FSInfo sector1;backup boot sector6;volume serial0x5446089b
```

Все смещения выше **относительно раздела**, кроме MBR start LBA32.
Первые8MiB раздела содержат reserved/boot/FSInfo и обе FAT, но не все directory data.

Уже сохранено:

- `analysis/fat_repair/mbr_before.bin` — только512B;
- `analysis/fat_repair/vbr_before.bin` — только512B;
- `analysis/fat_repair/geometry.json`;
- `analysis/fat_repair/handoff_preparation.json`;
- `analysis/fat_repair/handoff_stock_status.txt`.

**Полного backup FAT/каталогов/раздела ещё нет.** Исторические card backup-каталоги
есть, их актуальность для нынешнего состояния не проверена.

На консоли `fsck.fat`, `dosfsck`, `fsck.vfat` в PATH не найдены.
Скачан официальный release archive:

`modbuild/dosfstools-4.2.tar.gz` —320917B,
SHA256`64926eebf90092dca21b14259a5301b7b98e7b1943e8a201c7d726084809b527`.

URL https://github.com/dosfstools/dosfstools/releases/download/v4.2/dosfstools-4.2.tar.gz

Архив ещё не распакован/не собран; MIPS fsck binary не получен.

### Рекомендуемое продолжение ремонта

1. Восстановить сборочный WSL, собрать **статический MIPS32LE fsck.fat** из4.2.
   Проверить large-file support (`_FILE_OFFSET_BITS=64`), работу codepage437/iconv
   в RAMFS и команды/flags на тестовом образе. Одного отсутствия PT_INTERP недостаточно.
2. Подготовить отдельный repair kernel/initramfs с fsck внутри RAMFS. Frozen
   boot/driver init сначала монтирует SD, поэтому его нельзя выдавать за repair-init.
3. Все repair-артефакты доставить на SD до remount-ro. Разобраться с активным swapfile:
   swapoff перед чистой RO-передачей. При необходимости приостановить UI writers.
4. Sync + корректный remount-ro всех aliases/superblock; проверить реальные mounts.
   Сохранить служебные структуры и каталоги на ПК до исправлений. Не считать
   backup первых8MiB полным образом файловой системы.
5. В новом RAM-only ядре дождаться blockdev; **проверить, что SD не смонтирована**.
   Сначала `fsck.fat -n`, затем подходящий auto-repair и независимый повторный `-n`.
6. Не использовать немедленную запись `-w` и не прерывать запись forced reboot.
   В4.2 `-a` автоматически salvage unused chains; `-f` делает это явным.
   Exit1 означает наличие/внесение изменений, не автоматически fatal failure.
   Нужны stdout/stderr и постпроверка, а не только exitcode.
7. **Обычный30-секундный watchdog нельзя оставлять способным оборвать ремонт!**
   Repair-init должен отключить его на критическую запись либо обеспечить
   корректное обслуживание; автосброс выполнять после завершения fsck и sync.
   Нынешний frozen suite для такой операции не предназначен.
8. Сохранить отчёт, чисто завершить доступ к SD, вернуть stock и проверить boot hashes,
   интерфейс/настройки/данные. Ничего не форматировать и не менять NOR.

Эти шаги — план, не выполненные действия. В момент передачи ремонт не запускался.

## 9. Драйверы и прежний интерфейс

Матрица: `analysis/driver_port/PORT_MATRIX.ru.md`.
Статические AMPRPC notes: `analysis/driver_port/AMPRPC_NOTES.ru.md`.
Инвентаризация: `analysis/driver_port/stock_*.txt`, `stock_dtb_nodes.json`.

- 96 compatible nodes,70 enabled,38 unique enabled compatible;68 platform devices.
- 18 char devices используют общий avp-proxy. Экран, звук, MIPI/HDMI, codecs,
  standby и другие сервисы зависят от AMPRPC/kshm/mmz.
- AMPRPC в Linux7.2 ещё не перенесён. В notes есть реальные адреса функций,
  mailbox resources/IRQ66,8 message slots4KiB, layout open request и callback-проблемы.
- GPIO/pinctrl/serializer/input profile собран в `payload/kernel_lab_input`, но
  аппаратно не проверен. Порядок12 serial bits унаследован upstream и требует проверки.
- Restart handler и пассивный ADC/IIO собраны. ADC mapping проверен чтением
  регистров **в stock**, а не работой нового IIO-драйвера. Это не готовый battery driver.
- USB CDC/PIO profile ports несколько раз не перечислился. Не считать рабочим.
- Ранний64KiB RAM log утрачивался; новая partial-page trace после watchdog реально сохраняется.

Текущий интерфейс — TreeFrogUI/FrogUI в picoarch (`cores/frogui_libretro.so`).
В прежних maps наблюдались `driver_gb350.so`, `tfshim_gb350.so`;
device profile мог определяться как GB350, хотя железо — HC16E310/SF3000-клон.
Это же привело к несовпадению адресов nosleep для cubevol: патчи пропускались,
поэтому на время разработки cubevol удерживается STOP отдельным скриптом.

Сохранить меню/арт/звуки можно сохранением userspace и ресурсов, но нужно
обеспечить прежние backend ABI либо адаптировать userspace driver/plugin.
Не заменять интерфейс новым макетом без запроса. Старые .ko4.4 не загружаются
в7.2: нужны исходники/перенос, одна замена vermagic ничего не исправляет.
Сначала стабилизировать минимальную платформу и файловую передачу, затем
AMPRPC/AVP или совместимые framebuffer/audio backends, GPIO/кнопки, питание.

## 10. Остальные важные документы

- `analysis/KERNEL_AND_DRIVERS.ru.md` — подробная процедура и аппаратная приёмка, раздел14.
- `analysis/driver_port/AUTOREBOOT.ru.md` — watchdog, trace, история неудачных расширенных запусков.
- `analysis/FINDINGS.md` — хронология, до передачи пункт25; не путать старые гипотезы с новыми фактами.
- `scripts/kernel_lab/prepare_bundle.py` — offline build/emulation/fault tests/freeze.
- `scripts/kernel_lab/preflight.py`, `emulate_boot.py`, `tests/` — реальные проверки.
- `scripts/kernel_lab/acceptance.py`, `device_worker.py` — ограниченные WPD операции и аппаратный сценарий.

Главные правила продолжения: сохранять рабочий frozen baseline; не объявлять
скомпилированный драйвер аппаратно рабочим; не запускать fsck на RW-mounted SD;
не обрывать ремонт диагностическим watchdog; не запускать shutdown WSL вслепую.
