/**
 * Socket.IO client singleton.
 */
import { io, Socket } from 'socket.io-client';
import { WS_BASE_URL } from '@/lib/constants';

const SOCKET_URL = WS_BASE_URL;

let socket: Socket | null = null;

export function getSocket(): Socket {
  if (!socket) {
    socket = io(SOCKET_URL, {
      path: '/ws/socket.io',
      transports: ['websocket', 'polling'],
      autoConnect: false,
      reconnectionAttempts: 3,
      reconnectionDelay: 5000,
      timeout: 5000,
      auth: () => {
        const token = typeof window !== 'undefined'
          ? localStorage.getItem('baos_access_token')
          : null;
        return { token };
      },
    });
  }
  return socket;
}

export function connectSocket(): void {
  const s = getSocket();
  if (!s.connected) {
    s.connect();
  }
}

export function disconnectSocket(): void {
  if (socket?.connected) {
    socket.disconnect();
  }
}
