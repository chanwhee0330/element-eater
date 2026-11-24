# 오원 수호자 정면 애니메이션

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
