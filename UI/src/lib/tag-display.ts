/** Treat the legacy company label prefix as an alias of the canonical vendor prefix. */
export function tagsForDisplay(tags: string[]): string[] {
  return [...new Set(tags.map((tag) =>
    tag.startsWith("company:") ? `vendor:${tag.slice("company:".length)}` : tag,
  ))];
}
