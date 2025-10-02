"""
Slack message formatter - Convert markdown to Slack-friendly format
"""

import re


def format_for_slack(text: str) -> str:
    """
    Convert markdown text to Slack-friendly format

    Handles:
    - Markdown tables → Formatted text blocks
    - Bold ** → *bold*
    - Headers → Bold with emojis
    - Lists → Slack-friendly bullets

    Args:
        text: Markdown formatted text

    Returns:
        Slack-friendly formatted text
    """
    # Convert markdown bold (**text**) to Slack bold (*text*)
    text = re.sub(r'\*\*([^\*]+)\*\*', r'*\1*', text)

    # Convert markdown headers to Slack format
    text = re.sub(r'^### (.+)$', r'*\1*', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'*📊 \1*', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'*📈 \1*', text, flags=re.MULTILINE)

    # Convert markdown tables to formatted text
    text = _convert_tables(text)

    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _convert_tables(text: str) -> str:
    """Convert markdown tables to formatted text blocks"""
    lines = text.split('\n')
    result = []
    in_table = False
    table_data = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect table start (line with |)
        if '|' in line and not in_table:
            in_table = True
            table_data = []

            # Check if next line is separator (|---|---|)
            if i + 1 < len(lines) and re.match(r'\|[\s\-:|]+\|', lines[i + 1]):
                # This is a header row
                headers = [cell.strip() for cell in line.split('|') if cell.strip()]
                table_data.append(('header', headers))
                i += 2  # Skip header and separator
                continue
            else:
                # Regular table row
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                table_data.append(('row', cells))
                i += 1
                continue

        # Continue reading table rows
        elif '|' in line and in_table:
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:  # Skip empty rows
                table_data.append(('row', cells))
            i += 1
            continue

        # End of table
        elif in_table:
            in_table = False

            # Format the table
            formatted_table = _format_table(table_data)
            result.append(formatted_table)
            table_data = []

            # Add current non-table line
            result.append(line)
            i += 1

        # Regular line
        else:
            result.append(line)
            i += 1

    # Handle table at end of text
    if table_data:
        formatted_table = _format_table(table_data)
        result.append(formatted_table)

    return '\n'.join(result)


def _format_table(table_data: list) -> str:
    """Format table data as aligned text"""
    if not table_data:
        return ""

    # Separate headers and rows
    headers = None
    rows = []

    for row_type, cells in table_data:
        if row_type == 'header':
            headers = cells
        elif row_type == 'row':
            rows.append(cells)

    if not rows:
        return ""

    # Calculate column widths
    all_cells = [headers] if headers else []
    all_cells.extend(rows)

    num_cols = max(len(cells) for cells in all_cells)
    col_widths = [0] * num_cols

    for cells in all_cells:
        for i, cell in enumerate(cells):
            # Remove markdown bold for width calculation
            clean_cell = re.sub(r'\*\*([^\*]+)\*\*', r'\1', cell)
            col_widths[i] = max(col_widths[i], len(clean_cell))

    # Format the table
    result = []

    # Add header if exists
    if headers:
        header_line = "  ".join(
            cell.ljust(col_widths[i])
            for i, cell in enumerate(headers)
        )
        result.append(f"```\n{header_line}")
        result.append("-" * len(header_line))
    else:
        result.append("```")

    # Add rows
    for cells in rows:
        # Pad cells to match column count
        padded_cells = cells + [''] * (num_cols - len(cells))

        row_line = "  ".join(
            # Remove markdown bold for alignment
            re.sub(r'\*\*([^\*]+)\*\*', r'\1', cell).ljust(col_widths[i])
            for i, cell in enumerate(padded_cells[:num_cols])
        )
        result.append(row_line)

    result.append("```")

    return '\n'.join(result)


def create_slack_blocks(text: str) -> list:
    """
    Create Slack Block Kit blocks from formatted text

    Args:
        text: Formatted text

    Returns:
        List of Slack block dicts
    """
    blocks = []

    # Split into sections
    sections = text.split('\n\n')

    for section in sections:
        if not section.strip():
            continue

        # Code blocks (tables)
        if section.strip().startswith('```'):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": section
                }
            })
        # Regular text
        else:
            # Split long sections
            if len(section) > 3000:
                chunks = [section[i:i+3000] for i in range(0, len(section), 3000)]
                for chunk in chunks:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": chunk
                        }
                    })
            else:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": section
                    }
                })

        # Add divider between sections
        if len(blocks) > 0 and blocks[-1]["type"] != "divider":
            blocks.append({"type": "divider"})

    # Remove trailing divider
    if blocks and blocks[-1]["type"] == "divider":
        blocks.pop()

    return blocks


# Example usage
if __name__ == "__main__":
    test_markdown = """
# Portfolio Status

## Current Positions

| Symbol | Shares | Entry Price | Current P&L | % Change |
|--------|--------|-------------|-------------|----------|
| **AAPL** | 1 | $255.21 | -$0.26 | -0.10% |
| **MSFT** | 2 | $425.00 | +$5.50 | +0.65% |

### Account Summary

- **Total Value**: $100,000
- **Cash**: $50,000
- **Positions**: 2 active
"""

    formatted = format_for_slack(test_markdown)
    print("Formatted for Slack:")
    print(formatted)
    print("\n" + "="*60 + "\n")

    blocks = create_slack_blocks(formatted)
    print("Slack Blocks:")
    import json
    print(json.dumps(blocks, indent=2))
