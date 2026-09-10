import type { NashichanState } from "./types";

export const NASHICHAN_MESSAGES: Readonly<Record<NashichanState, string>> = {
  idle: "いつでもどうぞだよ",
  greeting: "よろしくね！",
  listening: "聞いてるよ",
  thinking: "確認してるよ",
  working: "いま処理中だよ",
  approval: "これで実行していい？",
  success: "終わったよ",
  celebrate: "やったー！すごいよ！",
  warning: "確認してほしいところがあるよ",
  error: "ここでエラーが出たよ",
  offline: "接続が切れてるみたい…",
  security: "セキュリティを確認中だよ",
  update: "アップデート中だよ",
  sleep: "少しおやすみ…",
};
