/**
 * useInstances Composable
 * 管理 MaiBot 实例的状态和业务逻辑
 */

import { ref, computed, reactive } from 'vue';
import {
  getInstances,
  getInstance,
  createInstance,
  updateInstance,
  deleteInstance,
  startInstance,
  stopInstance,
  restartInstance,
  getInstanceConfig,
  saveInstanceConfig,
  getRoutingRules,
  saveRoutingRules,
  getInstanceLogs,
  clearInstanceLogs,
  downloadInstanceLogs,
  type InstanceInfo,
  type RoutingRule
} from '@/utils/maibotApi';

// 实例列表
export const instances = ref<InstanceInfo[]>([]);

// 路由规则
export const routingRules = reactive<{
  default_instance: string;
  rules: RoutingRule[];
}>({
  default_instance: 'default',
  rules: []
});

// 加载状态
export const loading = ref(false);
export const instanceLoading = reactive<Record<string, boolean>>({});

// 错误信息
export const error = ref<string | null>(null);
export const instanceErrors = reactive<Record<string, string>>({});

// 实例日志
export const instanceLogs = reactive<Record<string, string[]>>({});

/**
 * 刷新实例列表
 */
export async function refreshInstances() {
  loading.value = true;
  error.value = null;
  try {
    instances.value = await getInstances();
  } catch (err: any) {
    error.value = err.message || '加载实例列表失败';
    console.error(error.value);
  } finally {
    loading.value = false;
  }
}

/**
 * 获取单个实例详情
 */
export async function fetchInstance(instanceId: string): Promise<InstanceInfo | null> {
  try {
    return await getInstance(instanceId);
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '获取实例详情失败';
    return null;
  }
}

/**
 * 创建新实例
 */
export async function createNewInstance(data: {
  instance_id: string;
  name: string;
  description?: string;
  port?: number;
  copy_from?: string;
  enable_webui?: boolean;
  enable_socket?: boolean;
}): Promise<boolean> {
  const instanceId = data.instance_id;
  instanceLoading[instanceId] = true;
  delete instanceErrors[instanceId];

  try {
    const newInstance = await createInstance(data);
    instances.value.push(newInstance);
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '创建实例失败';
    return false;
  } finally {
    instanceLoading[instanceId] = false;
  }
}

/**
 * 更新实例
 */
export async function updateInstanceInfo(
  instanceId: string,
  data: Partial<InstanceInfo>
): Promise<boolean> {
  instanceLoading[instanceId] = true;
  delete instanceErrors[instanceId];

  try {
    const updated = await updateInstance(instanceId, data);
    const index = instances.value.findIndex(i => i.id === instanceId);
    if (index >= 0) {
      instances.value[index] = updated;
    }
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '更新实例失败';
    return false;
  } finally {
    instanceLoading[instanceId] = false;
  }
}

/**
 * 删除实例
 */
export async function removeInstance(
  instanceId: string,
  deleteData: boolean = false
): Promise<boolean> {
  instanceLoading[instanceId] = true;
  delete instanceErrors[instanceId];

  try {
    await deleteInstance(instanceId, deleteData);
    instances.value = instances.value.filter(i => i.id !== instanceId);
    // 清理相关数据
    delete instanceLogs[instanceId];
    delete instanceErrors[instanceId];
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '删除实例失败';
    return false;
  } finally {
    instanceLoading[instanceId] = false;
  }
}

/**
 * 启动实例
 */
export async function startInstanceAsync(instanceId: string): Promise<boolean> {
  instanceLoading[instanceId] = true;
  delete instanceErrors[instanceId];

  try {
    await startInstance(instanceId);
    // 更新本地状态
    const instance = instances.value.find(i => i.id === instanceId);
    if (instance) {
      instance.status = 'starting';
      // 延迟后刷新以获取最新状态
      setTimeout(() => refreshInstances(), 1000);
    }
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '启动实例失败';
    return false;
  } finally {
    instanceLoading[instanceId] = false;
  }
}

/**
 * 停止实例
 */
export async function stopInstanceAsync(instanceId: string): Promise<boolean> {
  instanceLoading[instanceId] = true;
  delete instanceErrors[instanceId];

  try {
    await stopInstance(instanceId);
    // 更新本地状态
    const instance = instances.value.find(i => i.id === instanceId);
    if (instance) {
      instance.status = 'stopping';
      // 延迟后刷新以获取最新状态
      setTimeout(() => refreshInstances(), 1000);
    }
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '停止实例失败';
    return false;
  } finally {
    instanceLoading[instanceId] = false;
  }
}

/**
 * 重启实例
 */
export async function restartInstanceAsync(instanceId: string): Promise<boolean> {
  instanceLoading[instanceId] = true;
  delete instanceErrors[instanceId];

  try {
    await restartInstance(instanceId);
    // 更新本地状态
    const instance = instances.value.find(i => i.id === instanceId);
    if (instance) {
      instance.status = 'restarting';
      // 延迟后刷新以获取最新状态
      setTimeout(() => refreshInstances(), 1500);
    }
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '重启实例失败';
    return false;
  } finally {
    instanceLoading[instanceId] = false;
  }
}

/**
 * 获取实例配置
 */
export async function fetchInstanceConfig(instanceId: string): Promise<any> {
  try {
    return await getInstanceConfig(instanceId);
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '获取配置失败';
    return null;
  }
}

/**
 * 保存实例配置
 */
export async function saveInstanceConfigAsync(
  instanceId: string,
  config: any
): Promise<boolean> {
  instanceLoading[instanceId] = true;
  delete instanceErrors[instanceId];

  try {
    await saveInstanceConfig(instanceId, config);
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '保存配置失败';
    return false;
  } finally {
    instanceLoading[instanceId] = false;
  }
}

/**
 * 加载路由规则
 */
export async function loadRoutingRules(): Promise<boolean> {
  loading.value = true;
  error.value = null;

  try {
    const rules = await getRoutingRules();
    routingRules.default_instance = rules.default_instance || 'default';
    routingRules.rules = rules.rules || [];
    return true;
  } catch (err: any) {
    error.value = err.message || '加载路由规则失败';
    return false;
  } finally {
    loading.value = false;
  }
}

/**
 * 保存路由规则
 */
export async function saveRoutingRulesAsync(): Promise<boolean> {
  loading.value = true;
  error.value = null;

  try {
    await saveRoutingRules(routingRules);
    return true;
  } catch (err: any) {
    error.value = err.message || '保存路由规则失败';
    return false;
  } finally {
    loading.value = false;
  }
}

/**
 * 获取实例日志
 */
export async function fetchInstanceLogs(
  instanceId: string,
  limit: number = 100
): Promise<boolean> {
  try {
    const result = await getInstanceLogs(instanceId, limit);
    instanceLogs[instanceId] = result.logs;
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '获取日志失败';
    return false;
  }
}

/**
 * 清空实例日志
 */
export async function clearInstanceLogsAsync(instanceId: string): Promise<boolean> {
  try {
    await clearInstanceLogs(instanceId);
    instanceLogs[instanceId] = [];
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '清空日志失败';
    return false;
  }
}

/**
 * 下载实例日志
 */
export async function downloadInstanceLogsAsync(instanceId: string): Promise<boolean> {
  try {
    await downloadInstanceLogs(instanceId);
    return true;
  } catch (err: any) {
    instanceErrors[instanceId] = err.message || '下载日志失败';
    return false;
  }
}

/**
 * 计算属性：获取默认实例
 */
export const defaultInstance = computed(() => {
  return instances.value.find(i => i.is_default) || instances.value[0];
});

/**
 * 计算属性：获取运行中的实例
 */
export const runningInstances = computed(() => {
  return instances.value.filter(i => i.status === 'running');
});

/**
 * 计算属性：获取出错的实例
 */
export const errorInstances = computed(() => {
  return instances.value.filter(i => i.status === 'error');
});

/**
 * 使用 Hook
 */
export function useInstances() {
  return {
    // 状态
    instances,
    routingRules,
    instanceLogs,
    loading,
    error,
    instanceLoading,
    instanceErrors,

    // 计算属性
    defaultInstance,
    runningInstances,
    errorInstances,

    // 方法
    refreshInstances,
    fetchInstance,
    createNewInstance,
    updateInstanceInfo,
    removeInstance,
    startInstanceAsync,
    stopInstanceAsync,
    restartInstanceAsync,
    fetchInstanceConfig,
    saveInstanceConfigAsync,
    loadRoutingRules,
    saveRoutingRulesAsync,
    fetchInstanceLogs,
    clearInstanceLogsAsync,
    downloadInstanceLogsAsync
  };
}

export default useInstances;
