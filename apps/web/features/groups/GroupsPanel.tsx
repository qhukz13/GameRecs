"use client";

import { FormEvent } from "react";
import { Send, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiClient, Group } from "@/lib/api";
import { ConfirmDialog } from "@/components/ui/confirm";
import { useState } from "react";
import { useToast } from "@/components/ui/toast";

type GroupsPanelProps = {
  api: ApiClient;
  groups: Group[];
  selectedGroupId: string | null;
  onSelectGroup: (groupId: string) => void;
  onChanged: () => void;
  onError: (message: string) => void;
};

export function GroupsPanel({
  api,
  groups,
  selectedGroupId,
  onSelectGroup,
  onChanged,
  onError
}: GroupsPanelProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const toast = useToast();
  async function createGroup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.request<Group>("/groups", {
        method: "POST",
        body: JSON.stringify({ name: String(form.get("name")) })
      });
  if (event.currentTarget) event.currentTarget.reset();
      onChanged();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not create group");
    }
  }

  async function invite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedGroupId) return;
    const form = new FormData(event.currentTarget);
    try {
      await api.request(`/groups/${selectedGroupId}/invite`, {
        method: "POST",
        body: JSON.stringify({ username: String(form.get("username")) })
      });
  if (event.currentTarget) event.currentTarget.reset();
      onChanged();
    } catch (caught) {
      onError(caught instanceof Error ? caught.message : "Could not invite user");
    }
  }

  async function deleteGroup(groupId: string) {
    try {
      await api.delete(`/groups/${groupId}`);
      onChanged();
      toast.push("Group deleted", "success");
    } catch (caught) {
      const msg = caught instanceof Error ? caught.message : "Could not delete group";
      onError(msg);
      toast.push(msg, "error");
    }
  }

  function requestDelete(groupId: string) {
    setDeleteTarget(groupId);
    setConfirmOpen(true);
  }

  function onConfirmDelete() {
    if (!deleteTarget) return setConfirmOpen(false);
    deleteGroup(deleteTarget);
    setConfirmOpen(false);
    setDeleteTarget(null);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          Groups
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="flex gap-2" onSubmit={createGroup}>
          <Input name="name" placeholder="Weekend squad" required />
          <Button size="icon" title="Create group">
            <Users className="h-4 w-4" />
          </Button>
        </form>
        <div className="grid gap-2">
          {groups.map((group) => (
            <div key={group.id} className="flex gap-2">
              <Button
                className="justify-start flex-1"
                type="button"
                variant={selectedGroupId === group.id ? "default" : "outline"}
                onClick={() => onSelectGroup(group.id)}
              >
                {group.name}
              </Button>
              <Button size="icon" variant="ghost" title="Delete group" onClick={() => requestDelete(group.id)}>×</Button>
            </div>
          ))}
        </div>
        <form className="flex gap-2" onSubmit={invite}>
          <Input name="username" placeholder="Username" type="text" disabled={!selectedGroupId} required />
          <Button size="icon" title="Invite user" disabled={!selectedGroupId}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
      <ConfirmDialog
        open={confirmOpen}
        title="Delete group"
        description="This will remove the group and associated recommendations and memberships."
        onCancel={() => setConfirmOpen(false)}
        onConfirm={onConfirmDelete}
      />
    </Card>
  );
}

