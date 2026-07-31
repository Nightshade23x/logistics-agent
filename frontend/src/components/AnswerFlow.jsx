// COMPACT_FLOW_BOARD_V62
// SERPENTINE_FLOW_BOARD_V62
import { Fragment, useMemo } from "react";
import { useStore } from "../store.jsx";
import { connectorLabel, deriveProcessFlow } from "../utils/processFlow.jsx";

const NODES_PER_ROW = 4;

function chunkNodes(nodes) {
  const indexed = nodes.map((node, index) => ({ node, index }));
  const rows = [];

  for (let index = 0; index < indexed.length; index += NODES_PER_ROW) {
    rows.push(indexed.slice(index, index + NODES_PER_ROW));
  }

  return rows;
}

function NodeMeta({ node }) {
  return (
    <>
      {node.tab && <span className="process-flow-tab">Go to: {node.tab}</span>}
      {node.detail && <small>{node.detail}</small>}
      <span className="process-flow-status">
        {String(node.status || "review").replaceAll("_", " ")}
      </span>
    </>
  );
}

function DecisionNode({ node, index }) {
  return (
    <article
      className={`process-flow-node process-flow-kind-decision process-flow-tone-${node.tone}`}
      aria-label={`${index + 1}. ${node.label}`}
    >
      <div className="process-flow-decision-symbol">
        <svg viewBox="0 0 220 112" aria-hidden="true" focusable="false">
          <polygon points="110,2 218,56 110,110 2,56" />
        </svg>

        <div className="process-flow-decision-question">
          <span className="process-flow-index">{index + 1}</span>
          <strong>{node.label}</strong>
        </div>
      </div>

      <div className="process-flow-decision-meta">
        <NodeMeta node={node} />
      </div>
    </article>
  );
}

function StandardNode({ node, index }) {
  return (
    <article
      className={`process-flow-node process-flow-kind-${node.kind} process-flow-tone-${node.tone}`}
      aria-label={`${index + 1}. ${node.label}`}
    >
      <div className="process-flow-card-shape">
        <div className="process-flow-node-inner">
          <span className="process-flow-index">{index + 1}</span>
          <strong>{node.label}</strong>
          <NodeMeta node={node} />
        </div>
      </div>
    </article>
  );
}

function NodeShape({ node, index }) {
  if (node.kind === "decision") {
    return <DecisionNode node={node} index={index} />;
  }

  return <StandardNode node={node} index={index} />;
}

function RowConnector({ from, reverse }) {
  return (
    <div
      className={`process-flow-row-connector ${reverse ? "process-flow-row-connector-reverse" : ""}`}
      aria-hidden="true"
    >
      <span>{connectorLabel(from)}</span>
      <b>{reverse ? "←" : "→"}</b>
    </div>
  );
}

function RowBreakConnector({ from, side }) {
  return (
    <div
      className={`process-flow-row-break process-flow-row-break-${side}`}
      aria-hidden="true"
    >
      <span>{connectorLabel(from)}</span>
      <b>↓</b>
    </div>
  );
}

export default function AnswerFlow({ steps = [], result: suppliedResult = null }) {
  const store = useStore();
  const result = suppliedResult || store.result || null;
  const nodes = useMemo(() => deriveProcessFlow(result, steps), [result, steps]);
  const rows = useMemo(() => chunkNodes(nodes), [nodes]);

  if (!nodes.length) return null;

  return (
    <section
      className="answer-flow process-flow-v62 process-flow-board-v62"
      aria-labelledby="process-flow-title"
    >
      <div className="process-flow-heading">
        <div>
          <span className="process-flow-kicker">Next step flow</span>
          <h3 id="process-flow-title">Dynamic shipment process</h3>
        </div>
        <p>
          Follow the arrows from left to right, then down and back across the next row.
          The flow changes with the shipment, route, cargo risk, documents, insurance and cost status.
        </p>
      </div>

      <div
        className="process-flow-board"
        aria-label="Serpentine multi-row shipment process flowchart"
      >
        {rows.map((row, rowIndex) => {
          const reverse = rowIndex % 2 === 1;
          const side = reverse ? "left" : "right";

          return (
            <Fragment key={`row-${rowIndex}`}>
              <div className={`process-flow-board-row ${reverse ? "process-flow-board-row-reverse" : ""}`}>
                {row.map(({ node, index }, position) => (
                  <Fragment key={node.id}>
                    <NodeShape node={node} index={index} />
                    {position < row.length - 1 && (
                      <RowConnector from={node} reverse={reverse} />
                    )}
                  </Fragment>
                ))}
              </div>

              {rowIndex < rows.length - 1 && (
                <RowBreakConnector
                  from={row[row.length - 1].node}
                  side={side}
                />
              )}
            </Fragment>
          );
        })}
      </div>
    </section>
  );
}
