import React, { useState, useEffect } from 'react';
import { FlexSpacer } from '../components/Elements/SmallElements';
import { IconButton } from '../components/Elements/Button';
import { FaArrowAltCircleUp, FaMicrophone, FaPaperclip } from 'react-icons/fa';
import { useDispatch, useSelector } from 'react-redux';
import axios from '../utils/axios';
import { setLoadingDialog, setError } from '../store';
import constants from '../utils/constants';
import { Text } from '../components/Elements/Typography';
import NATextArea from '../components/Elements/TextAreas';
import { useNavigate } from 'react-router-dom';
import { MdOutlineSchedule } from 'react-icons/md';
import { GiBrain } from 'react-icons/gi';
import voice from '../services/voice';
import audioRecorder from '../services/audioRecorder';

import styled from 'styled-components';

const HomeDiv = styled.div`
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
`;

const Card = styled.div`
  border: thin solid rgba(255,255,255,0.3);
  border-radius: 20px;
  padding: 15px;
  width: 100%;
  max-width: 600px;
`;

const ToggleContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: var(--secondary-color);
`;

const ModeToggle = styled.button`
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: ${({ active }) => (active ? 'rgba(255,255,255,0.1)' : 'transparent')};
  color: #fff;
  border: thin solid rgba(255,255,255,0.3);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
  transition: background-color 0.2s ease;
  cursor: pointer;

  &:hover {
    background-color: rgba(255,255,255,0.1);
  }
`;


export default function Home() {
  const [messageText, setMessageText] = useState('');
  const [backgroundMode, setBackgroundMode] = useState(false);
  const [thinkingMode, setThinkingMode] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [autoSendVoice, setAutoSendVoice] = useState(false);
  const [useWhisper, setUseWhisper] = useState(false);
  const voiceSilenceMs = 2500;

  const accessToken = useSelector(state => state.accessToken);

  const dispatch = useDispatch();

  const navigate = useNavigate();

  const cancelRunningTask = (tid) => {
    dispatch(setLoadingDialog(true));
    axios.post(`/threads/${tid}/cancel_task`, {}, {
      headers: {
        'Authorization': 'Bearer ' + accessToken,
      }
    }).then((response) => {
      dispatch(setLoadingDialog(false));
      window.electronAPI.stopAIAgent();
    }).catch((error) => {
      dispatch(setLoadingDialog(false));
      if (error?.response?.status === constants.status.BAD_REQUEST) {
        dispatch(setError(true, constants.GENERAL_ERROR));
      } else {
        dispatch(setError(true, constants.GENERAL_ERROR));
      }
      setTimeout(() => {
        dispatch(setError(false, ''));
      }, 3000);
    });
  };

  const createThreadApi = async (text) => {
    const data = { task: text, background_mode: backgroundMode, extended_thinking_mode: thinkingMode };
    const response = await axios.post('/threads', data, {
      headers: { 'Authorization': 'Bearer ' + accessToken },
    });
    const res = response.data;
    if (res.type === 'desktop_task') {
      if (!backgroundMode && res.is_background_mode_requested) {
        const ready = await window.electronAPI.isBackgroundModeReady();
        if (!ready) {
          cancelRunningTask(res.thread_id);
          return res;
        }
      }
      setBackgroundMode(backgroundMode || res.is_background_mode_requested);
      setThinkingMode(thinkingMode || res.is_extended_thinking_mode_requested);
      window.electronAPI.setLastThinkingModeValue((thinkingMode || res.is_extended_thinking_mode_requested).toString());
      window.electronAPI.launchAIAgent(
        process.env.REACT_APP_PROTOCOL + '://' + process.env.REACT_APP_DNS,
        res.thread_id,
        backgroundMode || res.is_background_mode_requested
      );
    }
    return res;
  };

  const resetSilenceTimer = () => {
    if (!autoSendVoice) return;
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    silenceTimerRef.current = setTimeout(async () => {
      if (autoSendVoice && messageText.trim().length > 0) {
        try {
          dispatch(setLoadingDialog(true));
          const res = await createThreadApi(messageText.trim());
          dispatch(setLoadingDialog(false));
          if (res?.thread_id) {
            navigate('/threads/' + res.thread_id);
            window.location.reload();
          }
        } catch (e) {
          dispatch(setLoadingDialog(false));
          dispatch(setError(true, 'No se pudo crear el hilo con voz.'));
          setTimeout(() => dispatch(setError(false, '')), 2500);
        }
        stopVoice();
      }
    }, voiceSilenceMs);
  };

  const startVoice = () => {
    if (useWhisper) {
      try {
        const rec = audioRecorder.startRecording();
        rec.onStop(async (blob) => {
          setIsRecording(false);
          if (blob.size === 0) return;
          dispatch(setLoadingDialog(true));
          const formData = new FormData();
          formData.append('audio', blob, 'grabacion.webm');
          try {
            const response = await axios.post('/voice/transcribe', formData, {
              headers: { 'Authorization': 'Bearer ' + accessToken, 'Content-Type': 'multipart/form-data' }
            });
            const txt = (response.data?.text || '').trim();
            setMessageText(txt);
            dispatch(setLoadingDialog(false));
            if (autoSendVoice && txt.length > 0) {
              try {
                dispatch(setLoadingDialog(true));
                const res = await createThreadApi(txt);
                dispatch(setLoadingDialog(false));
                if (res?.thread_id) {
                  navigate('/threads/' + res.thread_id);
                  window.location.reload();
                }
              } catch (e) {
                dispatch(setLoadingDialog(false));
                dispatch(setError(true, 'No se pudo crear el hilo con la transcripción.'));
                setTimeout(() => dispatch(setError(false, '')), 2500);
              }
            }
          } catch (e) {
            dispatch(setLoadingDialog(false));
            dispatch(setError(true, 'Error transcribiendo audio.'));
            setTimeout(() => dispatch(setError(false, '')), 2500);
          }
        });
        rec.onError(() => { setIsRecording(false); });
        rec.promise.then(() => setIsRecording(true));
        recognitionRef.current = rec;
      } catch (e) {
        dispatch(setError(true, 'No se pudo iniciar grabación.'));
        setTimeout(() => dispatch(setError(false, '')), 2500);
      }
      return;
    }
    // Web Speech API path
    if (!voice.isSupported()) {
      dispatch(setError(true, 'Voz no soportada por este navegador.'));
      setTimeout(() => dispatch(setError(false, '')), 2500);
      return;
    }
    try {
      const lang = process.env.REACT_APP_VOICE_LANG || 'es-ES';
      const ctrl = voice.start({
        lang,
        onInterim: (txt) => { setMessageText(txt); resetSilenceTimer(); },
        onFinal: (txt) => { setMessageText((prev) => prev.trim().length === 0 ? txt : (prev + ' ' + txt)); resetSilenceTimer(); },
        onEnd: async () => {
          setIsRecording(false);
          if (autoSendVoice && messageText.trim().length > 0) {
            try {
              dispatch(setLoadingDialog(true));
              const res = await createThreadApi(messageText.trim());
              dispatch(setLoadingDialog(false));
              if (res?.thread_id) {
                navigate('/threads/' + res.thread_id);
                window.location.reload();
              }
            } catch (e) {
              dispatch(setLoadingDialog(false));
              dispatch(setError(true, 'No se pudo crear el hilo con voz.'));
              setTimeout(() => dispatch(setError(false, '')), 2500);
            }
          }
        },
        onError: () => setIsRecording(false),
      });
      recognitionRef.current = ctrl;
      setIsRecording(true);
      resetSilenceTimer();
    } catch (e) {
      setIsRecording(false);
    }
  };

  const stopVoice = () => {
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    if (recognitionRef.current) {
      recognitionRef.current.stop?.();
      recognitionRef.current = null;
    } else {
      voice.stop();
    }
    setIsRecording(false);
  };

  const onAttachClick = () => fileInputRef.current?.click();

  const onFileSelected = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      // 1) Crear hilo con texto base si está vacío
      const baseText = (messageText && messageText.trim().length > 0) ? messageText.trim() : `Analyze file: ${file.name}`;
      dispatch(setLoadingDialog(true));
      const res = await createThreadApi(baseText);
      if (!res?.thread_id) {
        dispatch(setLoadingDialog(false));
        dispatch(setError(true, 'No se pudo crear el hilo.'));
        setTimeout(() => dispatch(setError(false, '')), 2500);
        return;
      }
      // 2) Subir archivo al hilo creado
      const formData = new FormData();
      formData.append('upload', file);
      await axios.post(`/threads/${res.thread_id}/upload_file`, formData, {
        headers: { 'Authorization': 'Bearer ' + accessToken, 'Content-Type': 'multipart/form-data' },
      });
      dispatch(setLoadingDialog(false));
      navigate('/threads/' + res.thread_id);
      window.location.reload();
    } catch (err) {
      dispatch(setLoadingDialog(false));
      dispatch(setError(true, 'No se pudo subir el archivo.'));
      setTimeout(() => dispatch(setError(false, '')), 2500);
    } finally {
      e.target.value = '';
    }
  };

  const createThread = async () => {
    if (messageText.length === 0) {
      return;
    }
    const data = {task: messageText, background_mode: backgroundMode, extended_thinking_mode: thinkingMode};
    setMessageText('');
    dispatch(setLoadingDialog(true));
    axios.post('/threads', data, {
      headers: {
        'Authorization': 'Bearer ' + accessToken,
      }
    }).then(async (response) => {
      dispatch(setLoadingDialog(false));
      if (response?.data?.type === 'desktop_task') {
        if (!backgroundMode && response.data.is_background_mode_requested) {
          const ready = await window.electronAPI.isBackgroundModeReady();
          if (!ready) {
            cancelRunningTask();
            return;
          }
        }
        setBackgroundMode(backgroundMode || response.data.is_background_mode_requested);
        setThinkingMode(thinkingMode || response.data.is_extended_thinking_mode_requested);
        window.electronAPI.setLastThinkingModeValue((thinkingMode || response.data.is_extended_thinking_mode_requested).toString());
        window.electronAPI.launchAIAgent(
          process.env.REACT_APP_PROTOCOL + '://' + process.env.REACT_APP_DNS,
          response.data.thread_id,
          backgroundMode || response.data.is_background_mode_requested
        );
      }
      navigate('/threads/' + response.data.thread_id);
      window.location.reload();
    }).catch((error) => {
      dispatch(setLoadingDialog(false));
      if (error?.response?.status === constants.status.BAD_REQUEST) {
        if (error.response?.data?.message === 'Not_Browser_Task_BG_Mode') {
          dispatch(setError(true, 'Background Mode only supports browser tasks.'));
        } else {
          dispatch(setError(true, constants.GENERAL_ERROR));
        }
      } else {
        dispatch(setError(true, constants.GENERAL_ERROR));
      }
      setTimeout(() => {
        dispatch(setError(false, ''));
      }, 3000);
    });
  };

  const handleTextEnterKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      createThread();
    }
  };

  const onBGModeToggleChange = async (value) => {
    if (value) {
      const ready = await window.electronAPI.isBackgroundModeReady();
      if (!ready) {
        window.electronAPI.startBackgroundSetup();
        return;
      }
    }
    setBackgroundMode(value);
  };

  useEffect(() => {
    if (window.electronAPI?.onAIAgentLaunch) {
      window.electronAPI.onAIAgentLaunch((threadId) => {
        navigate('/threads/' + threadId);
        window.location.reload();
      });
    }
  }, []);

  useEffect(() => {
    if (window.electronAPI?.onAIAgentExit) {
      window.electronAPI.onAIAgentExit(() => {
        window.location.reload();
      });
    }
  }, []);

  useEffect(() => {
    const asyncTask = async () => {
      const lastBackgroundModeValue = await window.electronAPI.getLastBackgroundModeValue();
      setBackgroundMode(lastBackgroundModeValue === 'true');
    };
    asyncTask();
  }, []);

  useEffect(() => {
    const asyncTask = async () => {
      const lastThinkingModeValue = await window.electronAPI.getLastThinkingModeValue();
      setThinkingMode(lastThinkingModeValue === 'true');
    };
    asyncTask();
  }, []);

  const recognitionRef = React.useRef(null);
  const silenceTimerRef = React.useRef(null);
  const fileInputRef = React.useRef(null);

  return (
    <HomeDiv>
      <Text fontWeight='600' fontSize='23px' color='#fff'>
        Start a New Task
      </Text>
      <Card style={{marginTop: '15px'}}>
        <NATextArea
          background='transparent'
          isDarkMode
          padding='10px 4px'
          placeholder="What do you want NeuralAgent to do?"
          rows='3'
          value={messageText}
          onChange={(e) => setMessageText(e.target.value)}
          onKeyDown={handleTextEnterKey}
        />
        <input ref={fileInputRef} type='file' style={{ display: 'none' }} onChange={onFileSelected} />
        <div style={{marginTop: '10px', display: 'flex', alignItems: 'center'}}>
          <ToggleContainer>
            <ModeToggle
              active={backgroundMode}
              onClick={() => onBGModeToggleChange(!backgroundMode)}
            >
              <MdOutlineSchedule style={{fontSize: '19px'}} />
              Background
            </ModeToggle>
          </ToggleContainer>
          <div style={{width: '10px'}} />
          <ToggleContainer>
            <ModeToggle
              active={thinkingMode}
              onClick={() => setThinkingMode(!thinkingMode)}
            >
              <GiBrain style={{fontSize: '19px'}} />
              Thinking
            </ModeToggle>
          </ToggleContainer>
          <div style={{width: '10px'}} />
          <ToggleContainer>
            <ModeToggle active={autoSendVoice} onClick={() => setAutoSendVoice(!autoSendVoice)}>
              Auto-Send
            </ModeToggle>
          </ToggleContainer>
          <div style={{width: '10px'}} />
          <ToggleContainer>
            <ModeToggle active={useWhisper} onClick={() => setUseWhisper(!useWhisper)}>
              Whisper
            </ModeToggle>
          </ToggleContainer>
          <FlexSpacer isRTL={false} />
          <IconButton iconSize='24px' color='#fff' style={{ margin: '0 5px' }} onClick={onAttachClick}>
            <FaPaperclip />
          </IconButton>
          <div style={{width: '5px'}} />
          <IconButton iconSize='24px' color={isRecording ? '#ff5b5b' : '#fff'} style={{ margin: '0 5px' }} onClick={() => (isRecording ? stopVoice() : startVoice())}>
            <FaMicrophone />
          </IconButton>
          <div style={{width: '10px'}} />
          <IconButton
            iconSize='35px'
            color='#fff'
            disabled={messageText.length === 0}
            onClick={() => createThread()}
          >
            <FaArrowAltCircleUp />
          </IconButton>
        </div>
      </Card>
    </HomeDiv>
  );
}
