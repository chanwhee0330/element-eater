# 오원 수호자 애니메이션

원소별 PNG는 320×320 셀을 가로 6칸, 세로 10줄로 배치합니다. 모든 프레임의 발 기준점은 셀 왼쪽 위에서 (160, 264)입니다. JSON에는 Pico2D의 왼쪽 아래 원점으로 환산한 클리핑 좌표와 각 프레임의 지속 시간을 기록합니다.

| 형태 | PNG | JSON |
| --- | --- | --- |
| 불 | [시트](guardian-fire-animations.png) | [타임라인](guardian-fire-animations.json) |
| 바람 | [시트](guardian-wind-animations.png) | [타임라인](guardian-wind-animations.json) |
| 흙 | [시트](guardian-earth-animations.png) | [타임라인](guardian-earth-animations.json) |
| 번개 | [시트](guardian-lightning-animations.png) | [타임라인](guardian-lightning-animations.json) |
| 물 | [시트](guardian-water-animations.png) | [타임라인](guardian-water-animations.json) |

대기·이동은 각 12프레임, 공격·변신은 각 18프레임입니다. 전투에서 release 이벤트에 공격을 시작합니다. 변신은 기존 시트의 준비 동작과 무작위로 뽑힌 원소의 대기 동작을 연결하고, elementChange 이벤트에 상성을 바꿉니다. 전체 체력이 0이면 최종 성문을 엽니다.

`guardian-hit-masks.json`에는 대기·이동·공격별 몸체를 8픽셀 단위로 표본화한 피격 영역을 담았습니다. 투사체나 발밑 이펙트를 합성하기 전의 스프라이트로 생성합니다.

## 방향별 동작

원소별 `guardian-*-walk.png`와 JSON에는 네 방향 걷기 12프레임, 좌·우·위 대기 자세, 공격 18프레임, 변신 준비·정착 각 6프레임이 들어 있습니다. 정면 시트와 같은 320×320 셀과 발 기준점 (160, 264)을 사용합니다. 이동할 때는 실제 이동 방향, 공격할 때는 예고 시점의 조준 방향을 사용합니다. 변신할 때는 바라보던 방향을 유지하면서 새 원소의 정착 자세를 연결합니다. `guardian-walk-hit-masks.json`은 방향별 대기·걷기·공격 프레임의 피격 영역을 담습니다. 공격 발동과 원소 전환은 정면 클립과 같은 시점에 처리합니다.

`guardian-direction-planted.png`는 두 발을 디딘 오른쪽 원화입니다. `guardian-direction-rear.png`에는 등갑과 발뒤꿈치를 따로 디자인한 후면과 밑창이 드러나는 걸음 원화가 있습니다. `tools/build_guardian_walk.py`는 걷기의 지지 구간에서 발을 본체 이동과 반대 방향으로 보내고, 발을 들었을 때 앞으로 가져옵니다. 발목 아래의 부츠 모양을 유지합니다. 게임은 벽에 막히거나 대각선으로 움직일 때도 실제 이동량에 맞춰 보행 주기를 진행합니다. 공격과 변신은 두 발을 고정하며 왼쪽은 오른쪽을 반전해 만듭니다.

걷기 프레임에서는 다리 옆으로 뻗은 골반 갑옷과 자세 합성 후의 잔조각을 정리한 실루엣을 사용합니다.

브라우저에서 [동작 미리보기](../../../../outputs/previews/guardian/guardian-actions.html)를 열면 공격 이펙트를 확인할 수 있습니다. 걷기를 선택하면 방향별로 이동하는 모습과 발 교대 자세를 볼 수 있습니다. `tools/build_guardian_preview.py`는 현재 게임 아틀라스에서 독립 실행 HTML을 다시 만듭니다.

## 원소별 공격·변신 이펙트

`guardian-cast-effects.png`와 JSON에는 다섯 원소의 공격·변신 뒤/앞 레이어가 들어 있습니다. 각 레이어는 16프레임이며, 스프라이트의 공격 발동 또는 원소 전환 이벤트에 맞춰 방출 프레임을 선택합니다. `tools/build_guardian_effects.py`로 아틀라스를 다시 생성합니다. 게임과 HTML에서 같은 시트를 사용하며, HTML에서는 이펙트 표시를 끄고 장면을 비교할 수 있습니다.
