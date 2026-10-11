"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PageHeader } from "@/components/app/PageHeader";
import { Button } from "@/components/ui/button";
import { Field, Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api/client";
import { errorMessage, type Member } from "@/lib/hooks";

export default function MembersSettingsPage() {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: members = [], isLoading } = useQuery({
    queryKey: ["members"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/members");
      if (error) throw error;
      return data as Member[];
    },
  });

  const invite = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/members/invite", {
        body: { email, role: role as Member["role"] },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: async (data) => {
      await qc.invalidateQueries({ queryKey: ["members"] });
      setError(null);
      setEmail("");
      // Email delivery lands in a later milestone; surface the invite link for now.
      setNotice(`Invitation created for ${data?.email}. Dev invite token: ${data?.token}`);
    },
    onError: (e) => setError(errorMessage(e, "Could not send invitation.")),
  });

  return (
    <>
      <PageHeader title="Members" subtitle="Invite teammates and manage roles." />
      <div className="max-w-[820px] px-8 py-8 space-y-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            invite.mutate();
          }}
          className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]"
        >
          <h2 className="text-base font-semibold text-[var(--color-text)]">Invite a teammate</h2>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <div className="min-w-[260px] flex-1">
              <Field label="Email" htmlFor="inv-email">
                <Input id="inv-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </Field>
            </div>
            <div className="w-[160px]">
              <Field label="Role" htmlFor="inv-role">
                <Select id="inv-role" value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="admin">Admin</option>
                  <option value="member">Member</option>
                  <option value="viewer">Viewer</option>
                </Select>
              </Field>
            </div>
            <Button type="submit" disabled={invite.isPending}>
              {invite.isPending ? "Inviting…" : "Send invite"}
            </Button>
          </div>
          {error && <p className="mt-3 text-sm text-[var(--color-danger)]">{error}</p>}
          {notice && (
            <p className="mt-3 break-all rounded-[var(--radius-md)] bg-[var(--color-success-50)] px-3 py-2 text-xs text-[var(--color-text-body)]">
              {notice}
            </p>
          )}
        </form>

        <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-bg-subtle)] text-left text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
              <tr>
                <th className="px-4 py-2.5 font-semibold">Name</th>
                <th className="px-4 py-2.5 font-semibold">Email</th>
                <th className="px-4 py-2.5 font-semibold">Role</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={3} className="px-4 py-4 text-[var(--color-text-muted)]">
                    Loading…
                  </td>
                </tr>
              ) : (
                members.map((m) => (
                  <tr key={String(m.membership_id)} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3 font-medium text-[var(--color-text)]">{m.full_name ?? "—"}</td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)]">{m.email}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-[var(--color-primary-50)] px-2 py-0.5 text-xs font-medium capitalize text-[var(--color-primary)]">
                        {m.role}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
