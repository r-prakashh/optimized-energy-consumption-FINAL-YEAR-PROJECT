interface Props {
  lines: string[];
}

interface Group {
  main: string;
  subPoints: string[];
}

function groupLines(lines: string[]): Group[] {
  const groups: Group[] = [];
  for (const line of lines) {
    if (line.trim().startsWith("→")) {
      groups[groups.length - 1]?.subPoints.push(line.replace("→", "").trim());
    } else {
      groups.push({ main: line, subPoints: [] });
    }
  }
  return groups;
}

export function ActionPlan({ lines }: Props) {
  if (lines.length === 0) return null;
  const groups = groupLines(lines);

  return (
    <ol className="action-plan">
      {groups.map((group, i) => (
        <li key={i}>
          {group.main}
          {group.subPoints.length > 0 && (
            <ul className="action-plan-sub">
              {group.subPoints.map((sub, j) => (
                <li key={j}>{sub}</li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ol>
  );
}
