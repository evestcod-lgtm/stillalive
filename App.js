import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView, StyleSheet,
  Switch, FlatList, ActivityIndicator, Alert, SafeAreaView,
} from 'react-native';
import { WebView } from 'react-native-webview';
import Constants from 'expo-constants';

// ═══════════════════════════════════════════════════════════════
// Определение адреса бэкенда — по той же схеме, что и в SecureChat
// (см. www/boot.js там): при каждом запуске приложение само тянет
// свежий адрес из открытого файла в GitHub-репозитории. Пересборка
// APK при смене адреса туннеля больше не нужна вообще — только
// когда меняется сам код приложения.
//
// Порядок приоритета:
//  1. Свежий адрес из GitHub (patches/current-server-url.txt) — если
//     удалось получить при этом запуске.
//  2. EXPO_PUBLIC_API_URL / app.json extra.apiUrl — зашитый при сборке
//     фолбэк, на случай если GitHub недоступен при самом первом запуске.
//  3. localhost — совсем последний фолбэк для локальной разработки.
//
// ⚠️ Замени ссылку ниже на свой репозиторий/ветку, если они другие.
const SERVER_URL_LOOKUP =
  'https://raw.githubusercontent.com/evestcod-lgtm/stillalive/main/patches/current-server-url.txt';

const BAKED_API_BASE =
  process.env.EXPO_PUBLIC_API_URL ||
  Constants.expoConfig?.extra?.apiUrl ||
  'http://localhost:8000';

// Мутируемое значение — обновляется один раз при старте приложения,
// после чего используется всеми запросами через getApiBase().
let resolvedApiBase = BAKED_API_BASE;
let apiBaseReady = false;
let apiBaseReadyPromise = null;

function getApiBase() {
  return resolvedApiBase;
}

async function resolveApiBase() {
  if (apiBaseReadyPromise) return apiBaseReadyPromise;

  apiBaseReadyPromise = (async () => {
    try {
      const resp = await fetch(SERVER_URL_LOOKUP + '?t=' + Date.now());
      if (resp.ok) {
        const text = (await resp.text() || '').trim();
        if (text && text.indexOf('http') === 0) {
          resolvedApiBase = text;
          if (__DEV__) {
            console.log('[StillAlive] API_BASE (из GitHub) =', resolvedApiBase);
          }
        }
      }
    } catch (e) {
      // GitHub недоступен в момент запуска (нет интернета/rate limit) —
      // не страшно, остаёмся на BAKED_API_BASE, зашитом при сборке.
      if (__DEV__) {
        console.log('[StillAlive] Не удалось получить адрес из GitHub, использую фолбэк:', BAKED_API_BASE, e?.message);
      }
    } finally {
      apiBaseReady = true;
    }
    return resolvedApiBase;
  })();

  return apiBaseReadyPromise;
}

export default function App() {
  const [screen, setScreen] = useState('login');
  const [sessionId, setSessionId] = useState('');
  const [authMethod, setAuthMethod] = useState('browser'); // browser, manual
  const [creatureName, setCreatureName] = useState('Существо');
  const [language, setLanguage] = useState('ru');
  const [fontMode, setFontMode] = useState('normal');
  const [commentMode, setCommentMode] = useState(true);
  const [dmMode, setDmMode] = useState(true);
  const [targetInput, setTargetInput] = useState('');
  const [targets, setTargets] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef(null);
  const [apiReady, setApiReady] = useState(false);

  useEffect(() => {
    resolveApiBase()
      .then(() => restoreStateFromServer())
      .finally(() => {
        setApiReady(true);
        connectWebSocket();
      });
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Если бэкенд уже авторизован и/или охотится (например, сервер сам
  // перезапустился и восстановил состояние — см. state_store.py на
  // бэкенде), приложение при открытии сразу показывает актуальный
  // экран вместо формы логина, вместо того чтобы предлагать
  // подключаться заново к уже работающему боту.
  const restoreStateFromServer = async () => {
    try {
      const resp = await fetch(`${getApiBase()}/api/status`);
      if (!resp.ok) return;
      const status = await resp.json();

      if (status.creature_name) setCreatureName(status.creature_name);
      if (status.language) setLanguage(status.language);
      if (status.font_mode) setFontMode(status.font_mode);
      if (Array.isArray(status.targets)) setTargets(status.targets);

      if (status.authenticated) {
        setIsRunning(!!status.running);
        setScreen(status.running || (status.targets && status.targets.length > 0) ? 'control' : 'targets');
      }
    } catch (e) {
      // Бэкенд недоступен при старте — остаёмся на экране логина как раньше,
      // ничего страшного, это тот же путь, что был до этого изменения.
      if (__DEV__) {
        console.log('[StillAlive] Не удалось получить /api/status при старте:', e?.message);
      }
    }
  };

  const connectWebSocket = () => {
    try {
      const wsUrl = getApiBase().replace(/^http/, 'ws') + '/ws/logs';
      wsRef.current = new WebSocket(wsUrl);
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'log') {
            setLogs((prev) => [{time: new Date().toLocaleTimeString(), msg: data.message}, ...prev].slice(0, 100));
          }
        } catch (e) {
          console.log('WebSocket parse error');
        }
      };
    } catch (e) {
      console.log('WebSocket init failed');
    }
  };

  const handleBrowserAuth = (event) => {
    try {
      if (event.nativeEvent.data) {
        const data = JSON.parse(event.nativeEvent.data);
        if (data.sessionid) {
          setSessionId(data.sessionid);
          Alert.alert('✓ Успех', 'Session ID найден!');
          setScreen('settings');
        }
      }
    } catch (e) {
      console.log('Cookie parse error:', e);
    }
  };

  const injectCookieExtractor = `
    (function() {
      const sessionid = document.cookie
        .split('; ')
        .find(row => row.startsWith('sessionid='))
        ?.split('=')[1];
      
      if (sessionid) {
        window.ReactNativeWebView.postMessage(JSON.stringify({ sessionid }));
      }
    })();
  `;

  const handleConnect = async () => {
    if (!sessionId.trim()) {
      Alert.alert('Ошибка', 'Введите Session ID');
      return;
    }

    const apiBase = getApiBase();
    if (apiBase.includes('localhost') || apiBase.includes('127.0.0.1')) {
      Alert.alert(
        'Бэкенд не настроен',
        `Приложение пытается подключиться к ${apiBase}. Проверь, что бэкенд и туннель запущены в Termux (см. termux/README.md) — адрес подтягивается автоматически из GitHub при каждом запуске приложения.`
      );
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${apiBase}/api/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          auth_method: 'session',
          session_id: sessionId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        Alert.alert('✓ Успех', `Вход как @${data.username}`);
        setScreen('settings');
      } else {
        Alert.alert('✗ Ошибка', 'Аутентификация не удалась');
      }
    } catch (e) {
      Alert.alert('Ошибка', e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSettingsUpdate = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${getApiBase()}/api/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          creature_name: creatureName,
          language: language,
          font_mode: fontMode,
          comment_mode: commentMode,
          dm_mode: dmMode,
        }),
      });

      if (response.ok) {
        setScreen('targets');
      } else {
        Alert.alert('Ошибка', 'Не удалось обновить настройки');
      }
    } catch (e) {
      Alert.alert('Ошибка', e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddTarget = async () => {
    if (!targetInput.trim()) return;

    const newTargets = [...targets, targetInput.trim()];
    setTargets(newTargets);
    setTargetInput('');

    try {
      await fetch(`${getApiBase()}/api/targets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ usernames: newTargets }),
      });
      Alert.alert('✓', `Добавлен @${targetInput}`);
    } catch (e) {
      Alert.alert('Ошибка', e.message);
    }
  };

  const handleRemoveTarget = (idx) => {
    setTargets(targets.filter((_, i) => i !== idx));
  };

  const handleStart = async () => {
    if (targets.length === 0) {
      Alert.alert('Ошибка', 'Добавьте целевых пользователей');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${getApiBase()}/api/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'start' }),
      });

      if (response.ok) {
        setIsRunning(true);
      }
    } catch (e) {
      Alert.alert('Ошибка', e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${getApiBase()}/api/control`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'stop' }),
      });

      if (response.ok) {
        setIsRunning(false);
      }
    } catch (e) {
      Alert.alert('Ошибка', e.message);
    } finally {
      setLoading(false);
    }
  };

  // BROWSER LOGIN SCREEN
  if (screen === 'login' && authMethod === 'browser') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => setAuthMethod('manual')}>
            <Text style={styles.backButton}>← Ввод вручную</Text>
          </TouchableOpacity>
          <Text style={styles.title}>TikTok Логин</Text>
        </View>
        <WebView
          source={{ uri: 'https://www.tiktok.com/login' }}
          injectedJavaScript={injectCookieExtractor}
          onMessage={handleBrowserAuth}
          style={{ flex: 1 }}
        />
      </SafeAreaView>
    );
  }

  // MANUAL LOGIN SCREEN
  if (screen === 'login') {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView style={styles.screen}>
          <Text style={styles.title}>StillLife</Text>
          <Text style={styles.subtitle}>TikTok Бот</Text>

          <Text style={styles.label}>Способ входа</Text>
          <View style={styles.buttonGroup}>
            <TouchableOpacity
              style={[styles.tab, authMethod === 'browser' && styles.tabActive]}
              onPress={() => setAuthMethod('browser')}
            >
              <Text style={styles.tabText}>🌐 Браузер</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, authMethod === 'manual' && styles.tabActive]}
              onPress={() => setAuthMethod('manual')}
            >
              <Text style={styles.tabText}>✏️ Вручную</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>Session ID</Text>
          <TextInput
            style={styles.input}
            placeholder="Скопируйте sessionid cookie из TikTok"
            value={sessionId}
            onChangeText={setSessionId}
            secureTextEntry
          />

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleConnect}
            disabled={loading}
          >
            {loading ? <ActivityIndicator color="#000" /> : <Text style={styles.buttonText}>Вход</Text>}
          </TouchableOpacity>

          <Text style={styles.infoText}>
            📌 Как получить Session ID:{"\n"}
            1. Откройте TikTok в браузере{"\n"}
            2. F12 → Application → Cookies{"\n"}
            3. Найдите "sessionid"{"\n"}
            4. Скопируйте значение{"\n"}
            5. Вставьте выше
          </Text>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // SETTINGS SCREEN
  if (screen === 'settings') {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView style={styles.screen}>
          <Text style={styles.title}>Параметры Бота</Text>

          <Text style={styles.label}>Имя Существа</Text>
          <TextInput
            style={styles.input}
            placeholder="Существо"
            value={creatureName}
            onChangeText={setCreatureName}
          />

          <Text style={styles.label}>Язык</Text>
          <View style={styles.buttonGroup}>
            <TouchableOpacity
              style={[styles.tab, language === 'ru' && styles.tabActive]}
              onPress={() => setLanguage('ru')}
            >
              <Text style={styles.tabText}>🇷🇺 RU</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, language === 'en' && styles.tabActive]}
              onPress={() => setLanguage('en')}
            >
              <Text style={styles.tabText}>🇬🇧 EN</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>Шрифт</Text>
          <View style={styles.toggleRow}>
            <Text style={styles.text}>{fontMode === 'normal' ? 'Обычный' : 'Искажённый'}</Text>
            <Switch
              value={fontMode === 'distorted'}
              onValueChange={(val) => setFontMode(val ? 'distorted' : 'normal')}
            />
          </View>

          <Text style={styles.label}>Комментарии</Text>
          <Switch value={commentMode} onValueChange={setCommentMode} />

          <Text style={styles.label}>Прямые Сообщения</Text>
          <Switch value={dmMode} onValueChange={setDmMode} />

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleSettingsUpdate}
            disabled={loading}
          >
            {loading ? <ActivityIndicator color="#000" /> : <Text style={styles.buttonText}>Далее</Text>}
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // TARGETS SCREEN
  if (screen === 'targets') {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView style={styles.screen}>
          <Text style={styles.title}>Целевые Пользователи</Text>

          <View style={styles.inputGroup}>
            <TextInput
              style={[styles.input, {flex: 1}]}
              placeholder="@username"
              value={targetInput}
              onChangeText={setTargetInput}
            />
            <TouchableOpacity style={styles.addButton} onPress={handleAddTarget}>
              <Text style={styles.buttonText}>+</Text>
            </TouchableOpacity>
          </View>

          <FlatList
            data={targets}
            keyExtractor={(_, idx) => idx.toString()}
            renderItem={({ item, index }) => (
              <View style={styles.targetItem}>
                <Text style={styles.text}>@{item}</Text>
                <TouchableOpacity onPress={() => handleRemoveTarget(index)}>
                  <Text style={styles.deleteText}>✕</Text>
                </TouchableOpacity>
              </View>
            )}
            scrollEnabled={false}
          />

          <TouchableOpacity
            style={styles.button}
            onPress={() => setScreen('control')}
            disabled={targets.length === 0}
          >
            <Text style={styles.buttonText}>Начать ({targets.length})</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // CONTROL SCREEN
  if (screen === 'control') {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.screen}>
          <Text style={styles.title}>Управление</Text>

          <View style={styles.controlButtons}>
            <TouchableOpacity
              style={[styles.largeButton, isRunning && styles.running]}
              onPress={handleStart}
              disabled={isRunning || loading}
            >
              <Text style={styles.buttonText}>🔴 НАЧАТЬ</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.largeButton, styles.stopButton]}
              onPress={handleStop}
              disabled={!isRunning || loading}
            >
              <Text style={styles.buttonText}>⚫ СТОП</Text>
            </TouchableOpacity>
          </View>

          <Text style={styles.label}>Лог</Text>
          <FlatList
            data={logs}
            keyExtractor={(_, idx) => idx.toString()}
            renderItem={({ item }) => (
              <Text style={styles.logText}>[{item.time}] {item.msg}</Text>
            )}
            style={styles.logBox}
            scrollEnabled={false}
            nestedScrollEnabled={true}
          />
        </View>
      </SafeAreaView>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  screen: {
    flex: 1,
    padding: 16,
  },
  header: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#0f0',
  },
  backButton: {
    color: '#0f0',
    marginBottom: 8,
    fontSize: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#0ff',
    marginBottom: 8,
    textShadowColor: '#0f0',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 3,
  },
  subtitle: {
    fontSize: 14,
    color: '#0f0',
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#0f0',
    marginTop: 12,
    marginBottom: 6,
  },
  text: {
    fontSize: 13,
    color: '#ccc',
    fontFamily: 'monospace',
  },
  input: {
    borderWidth: 1,
    borderColor: '#0f0',
    backgroundColor: '#111',
    color: '#0ff',
    padding: 10,
    marginBottom: 12,
    borderRadius: 4,
    fontFamily: 'monospace',
    fontSize: 13,
  },
  inputGroup: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  addButton: {
    backgroundColor: '#0f0',
    paddingHorizontal: 16,
    borderRadius: 4,
    justifyContent: 'center',
  },
  button: {
    backgroundColor: '#0f0',
    padding: 12,
    borderRadius: 4,
    alignItems: 'center',
    marginTop: 16,
  },
  largeButton: {
    backgroundColor: '#0f0',
    paddingVertical: 32,
    borderRadius: 4,
    alignItems: 'center',
    marginBottom: 12,
  },
  stopButton: {
    backgroundColor: '#f00',
  },
  running: {
    backgroundColor: '#f00',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#000',
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  buttonGroup: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  tab: {
    flex: 1,
    backgroundColor: '#222',
    padding: 10,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#0f0',
    alignItems: 'center',
  },
  tabActive: {
    backgroundColor: '#0f0',
  },
  tabText: {
    color: '#000',
    fontWeight: '600',
  },
  targetItem: {
    backgroundColor: '#111',
    borderWidth: 1,
    borderColor: '#0f0',
    padding: 10,
    borderRadius: 4,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  deleteText: {
    color: '#f00',
    fontSize: 18,
    fontWeight: 'bold',
  },
  logBox: {
    backgroundColor: '#111',
    borderWidth: 1,
    borderColor: '#0f0',
    borderRadius: 4,
    padding: 8,
    maxHeight: 250,
  },
  logText: {
    fontSize: 11,
    color: '#0f0',
    fontFamily: 'monospace',
    marginBottom: 3,
  },
  controlButtons: {
    marginVertical: 16,
  },
  infoText: {
    color: '#0f0',
    fontSize: 12,
    marginTop: 16,
    fontStyle: 'italic',
  },
});


