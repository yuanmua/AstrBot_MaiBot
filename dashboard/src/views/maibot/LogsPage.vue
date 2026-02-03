<template>
  <v-container fluid class="py-6">
    <v-row>
      <!-- 实例选择侧边栏 -->
      <v-col cols="12" md="3">
        <v-card>
          <v-card-title>{{ tm("instances") }}</v-card-title>

          <v-list v-if="instances.length > 0">
            <v-list-item
              v-for="inst in instances"
              :key="inst.id"
              :active="selectedInstanceId === inst.id"
              @click="selectedInstanceId = inst.id"
              class="cursor-pointer"
            >
              <div class="d-flex align-center gap-2 w-100">
                <v-chip :color="getStatusColor(inst.status)" size="x-small">
                  {{ getStatusText(inst.status) }}
                </v-chip>
                <div class="flex-grow-1 text-truncate">
                  <div class="text-sm font-weight-bold">{{ inst.name }}</div>
                  <div class="text-caption text-grey">{{ inst.id }}</div>
                </div>
              </div>
            </v-list-item>
          </v-list>

          <div v-else class="text-center text-grey pa-4">暂无实例</div>
        </v-card>
      </v-col>

      <!-- 日志显示区域 -->
      <v-col cols="12" md="9">
        <InstanceLogPanel
          v-if="selectedInstanceId"
          :instance-id="selectedInstanceId"
        />

        <v-empty-state
          v-else
          headline="选择实例"
          text="请从左侧选择一个实例查看其日志"
          icon="mdi-file-document-outline"
        ></v-empty-state>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useInstances } from "@/composables/useInstances";
import InstanceLogPanel from "@/components/maibot/InstanceLogPanel.vue";
import { useModuleI18n } from "@/i18n/composables";
const { tm } = useModuleI18n("features/maibot");

const { instances, refreshInstances } = useInstances();

// UI 状态
const selectedInstanceId = ref("");

// 状态工具函数
const getStatusText = (status: string): string => {
  const map: Record<string, string> = {
    stopped: "已停止",
    starting: "启动中",
    running: "运行中",
    stopping: "停止中",
    error: "错误",
    restarting: "重启中",
  };
  return map[status] || "未知";
};

const getStatusColor = (status: string): string => {
  const map: Record<string, string> = {
    stopped: "grey",
    starting: "warning",
    running: "success",
    stopping: "warning",
    error: "error",
    restarting: "info",
  };
  return map[status] || "grey";
};

// 初始化
onMounted(async () => {
  await refreshInstances();
  if (instances.value.length > 0) {
    selectedInstanceId.value = instances.value[0].id;
  }
});
</script>

<style scoped lang="scss">
.cursor-pointer {
  cursor: pointer;
}
</style>
