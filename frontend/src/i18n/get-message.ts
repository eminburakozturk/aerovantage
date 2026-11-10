export type MessageTree = string | { [key: string]: MessageTree };

export function getMessage(messages: MessageTree, key: string): string | undefined {
  const parts = key.split(".");
  let current: MessageTree = messages;
  for (const part of parts) {
    if (typeof current !== "object" || current === null || !(part in current)) {
      return undefined;
    }
    current = current[part];
  }
  return typeof current === "string" ? current : undefined;
}

export function translate(
  messages: MessageTree,
  key: string,
  params?: Record<string, string | number>,
): string {
  const template = getMessage(messages, key) ?? key;
  if (!params) return template;
  return Object.entries(params).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
    template,
  );
}
