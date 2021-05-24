# Tabla de Hash Distribuida

## Autor

**Nombre y Apellidos** | **Correo** | **GitHub**
:-:|:-:|:-:
Ariel Plasencia Díaz | arielplasencia00@gmail.com | [@ArielXL](https://github.com/ArielXL)

## Chord

Chord es un protocolo de búsqueda distribuida que se puede utilizar para compartir archivos peer to peer (p2p). Chord distribuye objetos a través de una red dinámica de nodos e implementa un protocolo para encontrar estos objetos una vez que se han colocado en la red. La ubicación de los datos se implementa en la parte superior de Chord asociando una clave con cada elemento de datos y almacenando el par clave, elemento de datos en el nodo al que se asigna la clave. Cada nodo de esta red es un servidor capaz de buscar claves para aplicaciones clientes, pero también participa como almacén de claves. Además, se adapta de manera eficiente a medida que los nodos se unen y abandonan el sistema, y puede responder a consultas incluso si el sistema cambia continuamente. Por lo tanto, Chord es un sistema descentralizado en el que ningún nodo en particular es necesariamente un cuello de botella de rendimiento o un único punto de fallas.

### Llaves

Cada clave (basada en el nombre de un archivo) insertada en la tabla de hash distribuida (DHT) tiene un hash para que quepa en el espacio de claves admitido por la implementación particular de Chord. El espacio de claves, en esta implementación, reside entre $0$ y $2^{m} - 1$ inclusive, donde $m = 10$ (indicado por MAX_BITS en el código). Entonces, el espacio de claves está entre $0$ y $1023$.

### Anillo de nodos

Así como cada clave que se inserta en el DHT tiene un valor hash, cada nodo del sistema también tiene un valor hash en el espacio de claves del DHT. Para obtener este valor de hash, simplemente usamos el hash de la combinación de ip con puerto, usando el mismo algoritmo de hash que usamos para las claves de hash insertadas en el DHT. Chord ordena el nodo de forma circular, en la que el sucesor de cada nodo es el nodo con el siguiente hash más alto. El nodo con el hash más grande, sin embargo, tiene el nodo con el hash más pequeño como su sucesor. Es fácil imaginar los nodos colocados en un anillo, donde el sucesor de cada nodo es el nodo que le sigue cuando sigue una rotación en el sentido de las agujas del reloj.

### Superposición

Chord permite buscar cualquier clave en particular en $\log(n)$, donde $n$ es el número de nodos en la red. Para ello, emplea una inteligente red superpuesta que, cuando la topología de la red es estable, enruta las solicitudes al sucesor de una clave particular en $\log (n)$, donde $n$ es el número de nodos en la red. Esta búsqueda optimizada de sucesores es posible manteniendo una finger table por cada nodo. El número de filas en la finger table es igual a $m$ (indicado por MAX_BITS en el código).

### Resistencia a fallas

Chord admite la desconexión o falla desinformada de los nodos al hacer ping continuamente a su nodo sucesor. Al detectar un nodo desconectado, el anillo de nodos se estabilizará automáticamente. Los archivos en la red también se replican en el nodo sucesor, por lo que en caso de que un nodo falle, otro nodo se encarga de él, este último nodo será redirigido a su sucesor.
