import { Pipe, PipeTransform } from '@angular/core';
import { marked } from 'marked';

/**
 * Renders Claude's markdown reply to HTML. The result is bound with [innerHTML],
 * so Angular's built-in sanitizer strips anything unsafe.
 */
@Pipe({ name: 'markdown' })
export class MarkdownPipe implements PipeTransform {
  transform(value: string): string {
    return marked.parse(value ?? '', { async: false }) as string;
  }
}
