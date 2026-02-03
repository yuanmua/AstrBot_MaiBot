<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-robot</v-icon>
      {{ tm("configSections.bot.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-row>
        <!-- 平台 -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model="localConfig.platform"
            :label="tm('configSections.bot.platform')"
            variant="outlined"
            density="compact"
          />
        </v-col>

        <!-- QQ账号 -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model="localConfig.qq_account"
            :label="tm('configSections.bot.qq_account')"
            variant="outlined"
            density="compact"
          />
        </v-col>

        <!-- 昵称 -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model="localConfig.nickname"
            :label="tm('configSections.bot.nickname')"
            variant="outlined"
            density="compact"
          />
        </v-col>

        <!-- 其他平台账号 -->
        <v-col cols="12">
          <div class="text-subtitle-2 mb-2">
            {{ tm("configSections.bot.other_platforms") }}
          </div>
          <div
            v-for="(platform, index) in localConfig.platforms || []"
            :key="index"
            class="d-flex align-center mb-2"
          >
            <v-text-field
              v-model="localConfig.platforms[index]"
              variant="outlined"
              density="compact"
              hide-details
              class="flex-grow-1 mr-2"
              :placeholder="tm('configSections.bot.platform_placeholder')"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click="removePlatform(index)"
            />
          </div>
          <v-btn variant="outlined" size="small" @click="addPlatform">
            <v-icon start>mdi-plus</v-icon>
            {{ tm("configSections.bot.add_platform") }}
          </v-btn>
        </v-col>

        <!-- 别名 -->
        <v-col cols="12">
          <div class="text-subtitle-2 mb-2">
            {{ tm("configSections.bot.alias_names") }}
          </div>
          <div
            v-for="(alias, index) in localConfig.alias_names || []"
            :key="index"
            class="d-flex align-center mb-2"
          >
            <v-text-field
              v-model="localConfig.alias_names[index]"
              variant="outlined"
              density="compact"
              hide-details
              class="flex-grow-1 mr-2"
              :placeholder="tm('configSections.bot.alias_placeholder')"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click="removeAlias(index)"
            />
          </div>
          <v-btn variant="outlined" size="small" @click="addAlias">
            <v-icon start>mdi-plus</v-icon>
            {{ tm("configSections.bot.add_alias") }}
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useModuleI18n } from "@/i18n/composables";

const { tm } = useModuleI18n("features/maibot");

interface Props {
  config: Record<string, any>;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:config", config: Record<string, any>): void;
}>();

// 本地配置副本
const localConfig = ref({
  platform: props.config?.platform || "qq",
  qq_account: props.config?.qq_account || "",
  nickname: props.config?.nickname || "",
  platforms: props.config?.platforms || [],
  alias_names: props.config?.alias_names || [],
});

// 监听本地配置变化并通知父组件
watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);

// 添加/删除平台账号
const addPlatform = () => {
  localConfig.value.platforms = [...(localConfig.value.platforms || []), ""];
};

const removePlatform = (index: number) => {
  localConfig.value.platforms = localConfig.value.platforms.filter(
    (_: any, i: number) => i !== index,
  );
};

// 添加/删除别名
const addAlias = () => {
  localConfig.value.alias_names = [
    ...(localConfig.value.alias_names || []),
    "",
  ];
};

const removeAlias = (index: number) => {
  localConfig.value.alias_names = localConfig.value.alias_names.filter(
    (_: any, i: number) => i !== index,
  );
};
</script>
