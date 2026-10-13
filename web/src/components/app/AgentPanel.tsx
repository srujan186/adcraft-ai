"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Send, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { agentStore, useAgentOpen } from "@/lib/agentStore";

interface HelpLink { title: string; href: string }
interface Msg {
  role: "user" | "assistant";
  text: string;
  proposal?: { id: string; diff: string | null } | null;
  help?: HelpLink[];
}

function renderRich(text: string) {
  return text.split("\n").map((line, i) => (
    <Fragment key={i}>
      {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
        part.startsWith("**") && part.endsWith("**") ? <strong key={j}>{part.slice(2, -2)}</strong> : <span key={j}>{part}</span>,
      )}
      <br />
    </Fragment>
  ));
}

export function AgentPanel() {
  const open = useAgentOpen();
  const pathname = usePathname();
  const [threadId, setThreadId] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  const campaignId = pathname.match(/\/campaigns\/([0-9a-f-]+)/)?.[1];

  useEffect(() => {
    if (!open) return;
    (async () => {
      const { data } = await api.POST("/api/v1/agent/threads", { body: { context: { page: pathname, campaign_id: campaignId } } as never });
      setThreadId((data as { id: string })?.id ?? null);
      const sq = await api.GET("/api/v1/agent/suggested-questions", { params: { query: { section: campaignId ? "audience" : "default" } } });
      setSuggestions(((sq.data as { questions: string[] })?.questions) ?? []);
      const prefill = agentStore.takePrefill();
      if (prefill) void send(prefill, (data as { id: string })?.id);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  async function send(text: string, tid?: string | null) {
    const id = tid ?? threadId;
    if (!id || !text.trim()) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    const { data } = await api.POST("/api/v1/agent/threads/{thread_id}/messages", {
      params: { path: { thread_id: id } }, body: { message: text },
    });
    setBusy(false);
    const r = data as { answer: string; proposal: Msg["proposal"]; help?: HelpLink[] } | undefined;
    setMsgs((m) => [
      ...m,
      r
        ? { role: "assistant", text: r.answer, proposal: r.proposal, help: r.help }
        : { role: "assistant", text: "That message didn't go through. Check your connection and try again." },
    ]);
  }

  async function applyProposal(pid: string) {
    await api.POST("/api/v1/agent/proposals/{proposal_id}/apply", { params: { path: { proposal_id: pid } } });
    setMsgs((m) => [...m, { role: "assistant", text: "Done — I applied that change." }]);
  }

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && agentStore.close()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/30" />
        <Dialog.Content className="fixed right-0 top-0 z-50 flex h-full w-[min(440px,100vw)] flex-col bg-[var(--color-surface)] shadow-[var(--shadow-pop)]">
          <div className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
            <Dialog.Title className="flex items-center gap-2 font-semibold text-[var(--color-text)]">
              <Sparkles className="h-4 w-4 text-[var(--color-primary)]" /> Ask Agent
            </Dialog.Title>
            <Dialog.Close className="grid h-8 w-8 place-items-center rounded-full hover:bg-[var(--color-bg-subtle)]"><X className="h-4 w-4" /></Dialog.Close>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {msgs.length === 0 && (
              <div className="space-y-2">
                <p className="text-sm text-[var(--color-text-muted)]">Ask me about your campaigns, targeting, or how CTV works.</p>
                {suggestions.map((q) => (
                  <button key={q} onClick={() => send(q)} className="block w-full rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2 text-left text-sm text-[var(--color-text-body)] hover:bg-[var(--color-bg-subtle)]">
                    {q}
                  </button>
                ))}
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
                <div className={`max-w-[90%] rounded-[var(--radius-lg)] px-3 py-2 text-sm ${m.role === "user" ? "bg-[var(--color-primary)] text-white" : "bg-[var(--color-bg-subtle)] text-[var(--color-text-body)]"}`}>
                  {m.role === "assistant" ? renderRich(m.text) : m.text}
                  {m.help && m.help.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {m.help.map((h) => (
                        <li key={h.href}>
                          <Link href={h.href} target="_blank" className="font-medium text-[var(--color-primary)] underline-offset-2 hover:underline">
                            {h.title}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                  {m.proposal && (
                    <div className="mt-2 rounded-[var(--radius-md)] border border-[var(--color-primary)] bg-[var(--color-surface)] p-2 text-[var(--color-text-body)]">
                      <div className="text-xs">{m.proposal.diff}</div>
                      <div className="mt-1.5 flex gap-2">
                        <Button size="sm" onClick={() => applyProposal(m.proposal!.id)}>Apply</Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && <p className="text-xs text-[var(--color-text-muted)]">Working…</p>}
            <div ref={endRef} />
          </div>

          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex items-center gap-2 border-t border-[var(--color-border)] p-3">
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="What's on your mind?"
              className="h-9 flex-1 rounded-[var(--radius-md)] border border-[var(--color-border-strong)] px-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary-300)]" />
            <Button type="submit" size="icon" disabled={busy}><Send className="h-4 w-4" /></Button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
