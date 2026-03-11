'use client'

// AES-GCM 256-bit encryption for the user's OpenAI API key.
// All operations use the Web Crypto API (browser-native).
// The master key is derived from the user's password via PBKDF2.
// Only the encrypted blob (IV + ciphertext) and the salt are persisted in
// IndexedDB — the plaintext key never leaves browser memory.

const DB_NAME = 'agentflow_keystore'
const DB_VERSION = 1
const STORE_NAME = 'keys'
const KEY_RECORD_ID = 'agentflow_encrypted_key'

interface StoredKeyRecord {
  id: string
  salt: string    // hex-encoded
  iv: string      // hex-encoded
  ciphertext: string  // hex-encoded
}

function bufferToHex(buf: ArrayBuffer): string {
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

function hexToBuffer(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2)
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16)
  }
  return bytes
}

async function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME, { keyPath: 'id' })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function deriveKey(password: string, salt: Uint8Array): Promise<CryptoKey> {
  const enc = new TextEncoder()
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    enc.encode(password),
    'PBKDF2',
    false,
    ['deriveKey']
  )
  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt,
      iterations: 100_000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  )
}

/**
 * Encrypt and persist the OpenAI API key in IndexedDB.
 * The user's login password is used as the master password.
 */
export async function saveKey(apiKey: string, password: string): Promise<void> {
  const salt = crypto.getRandomValues(new Uint8Array(16))
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const cryptoKey = await deriveKey(password, salt)

  const enc = new TextEncoder()
  const ciphertext = await crypto.subtle.encrypt(
    { name: 'AES-GCM', iv },
    cryptoKey,
    enc.encode(apiKey)
  )

  const record: StoredKeyRecord = {
    id: KEY_RECORD_ID,
    salt: bufferToHex(salt),
    iv: bufferToHex(iv),
    ciphertext: bufferToHex(ciphertext),
  }

  const db = await openDB()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const req = tx.objectStore(STORE_NAME).put(record)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
  db.close()
}

/**
 * Decrypt and return the stored OpenAI API key.
 * Returns null if no key is stored or decryption fails.
 */
export async function loadKey(password: string): Promise<string | null> {
  const db = await openDB()
  const record = await new Promise<StoredKeyRecord | undefined>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const req = tx.objectStore(STORE_NAME).get(KEY_RECORD_ID)
    req.onsuccess = () => resolve(req.result as StoredKeyRecord | undefined)
    req.onerror = () => reject(req.error)
  })
  db.close()

  if (!record) return null

  try {
    const salt = hexToBuffer(record.salt)
    const iv = hexToBuffer(record.iv)
    const ciphertext = hexToBuffer(record.ciphertext)
    const cryptoKey = await deriveKey(password, salt)

    const plaintext = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv },
      cryptoKey,
      ciphertext
    )

    return new TextDecoder().decode(plaintext)
  } catch {
    // Wrong password or corrupted data
    return null
  }
}

/**
 * Returns true if an encrypted key record exists in IndexedDB.
 */
export async function hasKey(): Promise<boolean> {
  try {
    const db = await openDB()
    const record = await new Promise<unknown>((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const req = tx.objectStore(STORE_NAME).get(KEY_RECORD_ID)
      req.onsuccess = () => resolve(req.result)
      req.onerror = () => reject(req.error)
    })
    db.close()
    return record !== undefined
  } catch {
    return false
  }
}

/**
 * Remove the stored key from IndexedDB.
 */
export async function deleteKey(): Promise<void> {
  const db = await openDB()
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const req = tx.objectStore(STORE_NAME).delete(KEY_RECORD_ID)
    req.onsuccess = () => resolve()
    req.onerror = () => reject(req.error)
  })
  db.close()
}
